"""
원격 저장소 클론 캐시 관리자
세션 내에서 동일 원격 저장소의 로컬 클론을 재사용합니다.
캐시는 JSON 파일로 영구 저장되며, 만료 시간은 1일입니다.
"""

import os
import tempfile
import shutil
import hashlib
import logging
import json
import time
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime, timedelta
import git

logger = logging.getLogger(__name__)


class RepoCloneCache:
    """원격 저장소 클론 캐시 싱글톤"""

    _instance = None
    _cache: Dict[str, Dict] = {}  # {cache_key: {url, path, created_at, last_accessed}}
    _cache_dir: Optional[str] = None
    _cache_file: Optional[str] = None
    _expire_days: int = 1  # 캐시 만료 기간 (일)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """싱글톤 인스턴스를 강제로 리셋 (테스트/디버깅 용)"""
        cls._instance = None
        logger.info("Singleton instance reset")

    def _initialize(self):
        """캐시 디렉토리 및 메타데이터 초기화"""
        # Azure 환경 감지 및 적절한 캐시 디렉토리 설정
        cache_root = self._get_cache_root()
        self._cache_dir = str(cache_root / 'repos')
        self._cache_file = str(cache_root / 'cache_metadata.json')

        # 디렉토리 생성
        os.makedirs(self._cache_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)

        logger.info(f"Cache root: {cache_root}")
        logger.info(f"Initialized repository cache at: {self._cache_dir}")

        # Azure 환경에서 Git safe.directory 설정
        self._configure_git_safe_directory()

        # 기존 캐시 메타데이터 로드
        self._load_cache_metadata()

        # 간단한 유효성 검사만 수행 (만료/손상된 캐시만 제거)
        self._quick_validate_cache()

    def _get_cache_root(self) -> Path:
        """
        환경에 맞는 캐시 루트 디렉토리 결정

        Returns:
            Path: 캐시 루트 디렉토리
        """
        # 환경 변수로 캐시 디렉토리 명시적 지정 가능
        if 'REPO_CACHE_DIR' in os.environ:
            cache_dir = Path(os.environ['REPO_CACHE_DIR'])
            logger.info(f"Using cache dir from REPO_CACHE_DIR: {cache_dir}")
            return cache_dir

        # Azure Web App 환경 감지
        if os.path.exists('/home/site/wwwroot'):
            # Azure에서는 HOME 환경변수 사용 (일반적으로 /home)
            home_dir = os.environ.get('HOME', '/home')
            cache_dir = Path(home_dir) / '.cache'
            logger.info(f"Azure environment detected, HOME={home_dir}, using: {cache_dir}")
            return cache_dir

        # Linux 환경에서는 /tmp 사용 (선택적으로 영구 디렉토리)
        if os.name == 'posix':
            # 먼저 $HOME/.cache 시도 (영구적)
            if 'HOME' in os.environ:
                cache_dir = Path(os.environ['HOME']) / '.cache' / 'git_history_gen'
                logger.info(f"Using HOME cache dir: {cache_dir}")
                return cache_dir
            # 그렇지 않으면 /tmp (재시작 시 삭제됨)
            cache_dir = Path(tempfile.gettempdir()) / 'git_history_gen_cache'
            logger.info(f"Using temp cache dir: {cache_dir}")
            return cache_dir

        # Windows나 기타 환경에서는 프로젝트 루트 사용
        project_root = Path(__file__).parent.parent.resolve()
        cache_dir = project_root / '.cache'
        logger.info(f"Using project cache dir: {cache_dir}")
        return cache_dir

    def _configure_git_safe_directory(self):
        """
        Git safe.directory 설정 (Azure 환경 등에서 소유권 문제 방지)
        - 이미 존재하는 항목은 중복 추가하지 않음
        - '*'가 없으면 한 번만 추가
        - 기존 중복 항목이 있다면 정리
        """
        try:
            import subprocess

            existing = self._get_safe_directories()
            if '*' not in existing:
                subprocess.run(
                    ['git', 'config', '--global', '--add', 'safe.directory', '*'],
                    capture_output=True,
                    timeout=5,
                    text=True,
                    check=False,
                )
                logger.info("✓ Configured Git safe.directory: *")
            else:
                logger.debug("safe.directory already contains '*'")

            # 중복 정리 (모든 항목 대상, 순서 유지)
            self._cleanup_safe_directory_duplicates()

        except FileNotFoundError:
            logger.warning("Git command not found, skipping safe.directory configuration")
        except Exception as e:
            logger.warning(f"Failed to configure safe.directory (non-critical): {e}")

    def _get_safe_directories(self) -> list[str]:
        """현재 설정된 safe.directory 목록을 반환"""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'config', '--global', '--get-all', 'safe.directory'],
                capture_output=True,
                timeout=5,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                entries = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                return entries
        except Exception as e:
            logger.debug(f"Failed to read safe.directory: {e}")
        return []

    def _cleanup_safe_directory_duplicates(self):
        """safe.directory 항목 중복을 제거하고 유일 항목만 보존"""
        try:
            import subprocess
            entries = self._get_safe_directories()
            if not entries:
                return

            unique = []
            seen = set()
            for e in entries:
                key = os.path.normcase(os.path.normpath(e)) if e != '*' else '*'
                if key not in seen:
                    seen.add(key)
                    unique.append(e)

            if unique == entries:
                return  # 이미 중복 없음

            # 전체 항목 제거 후 유니크 항목만 재등록
            subprocess.run(
                ['git', 'config', '--global', '--unset-all', 'safe.directory'],
                capture_output=True,
                timeout=5,
                text=True,
                check=False,
            )

            for e in unique:
                subprocess.run(
                    ['git', 'config', '--global', '--add', 'safe.directory', e],
                    capture_output=True,
                    timeout=5,
                    text=True,
                    check=False,
                )
            logger.info(f"✓ Deduplicated safe.directory entries: {len(entries)} -> {len(unique)}")
        except FileNotFoundError:
            logger.debug("Git not found while deduplicating safe.directory")
        except Exception as e:
            logger.debug(f"Failed to deduplicate safe.directory: {e}")

    def _add_safe_directory(self, repo_path: str):
        """
        특정 저장소 경로를 Git safe.directory에 추가
        - '*'가 이미 있으면 개별 경로 추가 불필요
        - 동일 경로가 이미 있으면 중복 추가하지 않음
        Args:
            repo_path: 저장소 경로
        """
        try:
            import subprocess

            entries = self._get_safe_directories()
            # '*'가 있으면 모든 디렉토리 허용됨 → 스킵
            if '*' in entries:
                logger.debug("'*' present in safe.directory; skipping per-repo add")
                return

            # 경로 정규화로 중복 방지 (Windows 대소문자/슬래시 차이 보정)
            target = os.path.normcase(os.path.normpath(repo_path))
            normalized_set = {os.path.normcase(os.path.normpath(e)) for e in entries}

            if target in normalized_set:
                logger.debug(f"safe.directory already contains: {repo_path}")
                return

            result = subprocess.run(
                ['git', 'config', '--global', '--add', 'safe.directory', repo_path],
                capture_output=True,
                timeout=5,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                logger.info(f"✓ Added safe.directory: {repo_path}")
            else:
                logger.debug(f"Failed to add safe.directory (non-critical): {result.stderr}")
        except FileNotFoundError:
            logger.debug("Git command not found")
        except Exception as e:
            logger.debug(f"Failed to add safe.directory (non-critical): {e}")

    def _ensure_commit_exists(self, repo_path: str, repo_url: str, commit_sha: str) -> bool:
        """
        특정 커밋이 로컬 저장소에 존재하는지 확인하고, 없으면 fetch

        Args:
            repo_path: 로컬 저장소 경로
            repo_url: 원격 저장소 URL
            commit_sha: 확인할 커밋 SHA

        Returns:
            bool: 커밋이 존재하면 True
        """
        try:
            repo = git.Repo(repo_path)

            # 커밋이 존재하는지 확인
            try:
                repo.commit(commit_sha)
                logger.debug(f"Commit {commit_sha[:8]} exists locally")
                return True
            except (git.exc.BadName, ValueError):
                # 커밋이 없으면 fetch 시도
                logger.info(f"Commit {commit_sha[:8]} not found, fetching...")

                origin = repo.remotes.origin

                # 특정 커밋을 포함하도록 더 깊게 fetch
                try:
                    # 먼저 depth를 늘려서 fetch
                    origin.fetch(depth=1000)

                    # 다시 확인
                    try:
                        repo.commit(commit_sha)
                        logger.info(f"✓ Fetched commit {commit_sha[:8]}")
                        return True
                    except:
                        # 여전히 없으면 전체 히스토리 fetch
                        logger.info(f"Fetching full history for commit {commit_sha[:8]}...")
                        origin.fetch(unshallow=True)

                        repo.commit(commit_sha)
                        logger.info(f"✓ Fetched commit {commit_sha[:8]} (full history)")
                        return True

                except Exception as e:
                    logger.warning(f"Failed to fetch commit {commit_sha[:8]}: {e}")
                    return False

        except Exception as e:
            logger.error(f"Error checking commit existence: {e}")
            return False

    def _load_cache_metadata(self):
        """캐시 메타데이터를 JSON 파일에서 로드"""
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded cache metadata: {len(self._cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
                self._cache = {}
        else:
            logger.info("No existing cache metadata found")
            self._cache = {}

    def _save_cache_metadata(self):
        """캐시 메타데이터를 JSON 파일에 저장"""
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            logger.debug("Saved cache metadata")
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def _quick_validate_cache(self):
        """빠른 캐시 검증 (만료 및 경로 존재만 체크, fetch는 안함)"""
        logger.info("Quick validating cache entries...")

        invalid_keys = []
        expired_keys = []
        now = datetime.now()

        for cache_key, entry in self._cache.items():
            try:
                cache_path = entry['path']
                cache_path = self._normalize_cache_path(cache_path, cache_key)
                entry['path'] = cache_path

                created_at = datetime.fromisoformat(entry['created_at'])
                repo_url = entry['url']

                # 만료 확인
                if now - created_at > timedelta(days=self._expire_days):
                    logger.info(f"Cache expired: {repo_url}")
                    expired_keys.append(cache_key)
                    continue

                # 경로 존재 확인만
                if not os.path.exists(cache_path):
                    logger.warning(f"Cache path not found: {cache_path}")
                    invalid_keys.append(cache_key)
                    continue

                # Git 저장소 유효성만 확인 (fetch는 안함)
                try:
                    repo = git.Repo(cache_path)
                    repo.close()
                    logger.debug(f"✓ Valid cache entry: {repo_url}")
                except Exception as e:
                    logger.warning(f"Invalid git repository: {cache_path} - {e}")
                    invalid_keys.append(cache_key)

            except Exception as e:
                logger.warning(f"Failed to validate cache entry {cache_key}: {e}")
                invalid_keys.append(cache_key)

        # 만료/손상된 캐시만 정리
        removed_count = 0
        for cache_key in expired_keys + invalid_keys:
            self._invalidate_cache(cache_key)
            removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} invalid/expired cache entries")
            self._save_cache_metadata()
        else:
            logger.info("All cache entries are valid")

    def _validate_single_repo(self, cache_key: str) -> bool:
        """
        특정 저장소의 캐시 유효성 검사 및 업데이트

        Args:
            cache_key: 캐시 키

        Returns:
            bool: 유효하면 True, 아니면 False
        """
        if cache_key not in self._cache:
            return False

        try:
            entry = self._cache[cache_key]
            cache_path = entry['path']
            repo_url = entry['url']

            # safe.directory 설정
            self._add_safe_directory(cache_path)

            # Git 저장소 유효성 확인 및 업데이트
            repo = git.Repo(cache_path)
            logger.info(f"Fetching latest changes for: {repo_url}")
            origin = repo.remotes.origin
            origin.fetch()
            repo.git.reset('--hard', 'origin/HEAD')

            # 마지막 접근 시간 업데이트
            entry['last_accessed'] = datetime.now().isoformat()
            self._save_cache_metadata()

            logger.info(f"✓ Updated cache entry: {repo_url}")
            return True

        except Exception as e:
            logger.warning(f"Failed to validate cache entry {cache_key}: {e}")
            return False

    def _validate_and_cleanup_cache(self):
        """캐시 유효성 검사 및 만료/손상된 캐시 정리 (전체 검증 - 사용 안함)"""
        logger.info("Validating cache entries...")

        invalid_keys = []
        expired_keys = []
        now = datetime.now()

        for cache_key, entry in self._cache.items():
            try:
                cache_path = entry['path']
                # 경로 정규화
                cache_path = self._normalize_cache_path(cache_path, cache_key)
                entry['path'] = cache_path  # 정규화된 경로로 업데이트

                created_at = datetime.fromisoformat(entry['created_at'])
                repo_url = entry['url']

                # 만료 확인
                if now - created_at > timedelta(days=self._expire_days):
                    logger.info(f"Cache expired: {repo_url} (age: {(now - created_at).days} days)")
                    expired_keys.append(cache_key)
                    continue

                # 경로 존재 확인
                if not os.path.exists(cache_path):
                    logger.warning(f"Cache path not found: {cache_path}")
                    invalid_keys.append(cache_key)
                    continue

                # Git 저장소 유효성 확인 및 업데이트
                try:
                    repo = git.Repo(cache_path)

                    # 유효한 캐시는 최신화 시도
                    logger.info(f"Updating cached repository: {repo_url}")
                    origin = repo.remotes.origin
                    origin.fetch()
                    repo.git.reset('--hard', 'origin/HEAD')

                    # 마지막 접근 시간 업데이트
                    entry['last_accessed'] = now.isoformat()

                    logger.info(f"✓ Valid cache entry: {repo_url}")

                except git.exc.GitCommandError as e:
                    logger.warning(f"Git operation failed for {cache_path}: {e}")
                    invalid_keys.append(cache_key)
                except Exception as e:
                    logger.warning(f"Invalid git repository: {cache_path} - {e}")
                    invalid_keys.append(cache_key)

            except Exception as e:
                logger.warning(f"Failed to validate cache entry {cache_key}: {e}")
                invalid_keys.append(cache_key)

        # 만료/손상된 캐시 정리
        removed_count = 0
        for cache_key in expired_keys + invalid_keys:
            self._invalidate_cache(cache_key)
            removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} invalid/expired cache entries")
            self._save_cache_metadata()
        else:
            logger.info("All cache entries are valid")

    def _get_cache_key(self, repo_url: str) -> str:
        """저장소 URL에서 캐시 키 생성"""
        url_hash = hashlib.md5(repo_url.encode()).hexdigest()[:12]
        return url_hash

    def _normalize_cache_path(self, path: str, cache_key: str) -> str:
        """
        캐시 경로를 정규화합니다. 잘못된 경로 패턴을 감지하고 수정합니다.

        Args:
            path: 원본 경로
            cache_key: 캐시 키

        Returns:
            정규화된 경로
        """
        # 잘못된 패턴 감지: git_history_gen.cache (백슬래시 없이 점으로 붙어있음)
        if 'git_history_gen.cache' in path:
            logger.warning(f"Detected malformed path pattern: {path}")
            # 올바른 경로로 수정
            correct_path = os.path.join(self._cache_dir, cache_key)
            logger.info(f"Corrected path: {correct_path}")
            return correct_path

        # 경로가 _cache_dir로 시작하지 않으면 재구성
        if not path.startswith(self._cache_dir):
            logger.warning(f"Path does not start with cache_dir: {path}")
            correct_path = os.path.join(self._cache_dir, cache_key)
            logger.info(f"Reconstructed path: {correct_path}")
            return correct_path

        return path

    def _force_remove_directory(self, path: str, max_retries: int = 3):
        """
        디렉토리를 강제로 삭제합니다 (다중 시도).

        Args:
            path: 삭제할 디렉토리 경로
            max_retries: 최대 재시도 횟수
        """
        import stat
        import subprocess

        for attempt in range(max_retries):
            try:
                if not os.path.exists(path):
                    return  # 이미 삭제됨

                logger.info(f"Attempting to remove directory (attempt {attempt + 1}/{max_retries}): {path}")

                # 시도 1: 일반 삭제
                try:
                    shutil.rmtree(path)
                    time.sleep(0.3)  # Windows 파일시스템 동기화 대기
                    if not os.path.exists(path):
                        logger.info(f"✓ Successfully removed: {path}")
                        return
                    logger.debug(f"Directory still exists after normal removal")
                except Exception as e:
                    logger.debug(f"Normal removal failed: {e}")

                # 시도 2: 읽기 전용 속성 제거 후 삭제
                try:
                    def remove_readonly(func, path, _):
                        try:
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        except:
                            pass

                    time.sleep(0.5)  # 파일 핸들 해제 대기
                    shutil.rmtree(path, onerror=remove_readonly)
                    time.sleep(0.5)  # 삭제 완료 대기

                    if not os.path.exists(path):
                        logger.info(f"✓ Force-removed with readonly fix: {path}")
                        return
                    logger.debug(f"Directory still exists after readonly removal")
                except Exception as e:
                    logger.debug(f"Readonly removal failed: {e}")

                # 시도 3: 디렉토리 이름 변경 후 삭제 (Windows에서 효과적)
                try:
                    import uuid
                    temp_name = os.path.join(os.path.dirname(path), f"_temp_delete_{uuid.uuid4().hex[:8]}")

                    # 디렉토리 이름 변경 (파일이 잠겨있어도 가능)
                    os.rename(path, temp_name)
                    logger.info(f"Renamed directory: {path} -> {temp_name}")

                    time.sleep(0.5)

                    # 이름 바꾼 디렉토리 삭제 시도
                    try:
                        shutil.rmtree(temp_name, ignore_errors=True)
                        time.sleep(0.5)  # 삭제 완료 대기
                    except:
                        pass

                    if not os.path.exists(path):
                        logger.info(f"✓ Removed using rename strategy: {path}")
                        # 이름 바꾼 디렉토리가 남아있다면 백그라운드에서 계속 시도
                        if os.path.exists(temp_name):
                            logger.warning(f"Renamed directory still exists, will retry: {temp_name}")
                            # 비동기 삭제 재시도 (무시)
                            try:
                                shutil.rmtree(temp_name, ignore_errors=True)
                            except:
                                pass
                        return
                    logger.debug(f"Original path still exists after rename strategy")
                except Exception as e:
                    logger.debug(f"Rename removal failed: {e}")

                # 시도 4: Windows robocopy로 빈 디렉토리 덮어쓰기 후 삭제
                try:
                    temp_empty = tempfile.mkdtemp()
                    try:
                        # robocopy: 빈 디렉토리로 덮어쓰기 (파일 삭제 효과)
                        result = subprocess.run(
                            ['robocopy', temp_empty, path, '/mir', '/w:1', '/r:1'],
                            capture_output=True,
                            timeout=30
                        )
                        # robocopy exit code 0-7은 성공
                        if result.returncode <= 7:
                            time.sleep(0.5)
                            shutil.rmtree(path, ignore_errors=True)
                            shutil.rmtree(temp_empty, ignore_errors=True)
                            logger.info(f"✓ Removed using robocopy: {path}")
                            return
                    finally:
                        try:
                            shutil.rmtree(temp_empty, ignore_errors=True)
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"Robocopy removal failed: {e}")

                # 시도 5: rmdir 시스템 명령
                try:
                    result = subprocess.run(
                        ['cmd', '/c', 'rmdir', '/s', '/q', path],
                        capture_output=True,
                        timeout=30
                    )
                    time.sleep(0.5)
                    if not os.path.exists(path):
                        logger.info(f"✓ Removed using rmdir: {path}")
                        return
                except Exception as e:
                    logger.debug(f"Rmdir removal failed: {e}")

                # 재시도 전 대기
                if attempt < max_retries - 1:
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")

        # 모든 시도 실패
        logger.error(f"⚠️ Failed to remove directory after {max_retries} attempts: {path}")
        logger.error(f"⚠️ Manual cleanup required!")
        raise Exception(f"Cannot remove directory: {path}")

    def get_or_clone(self, repo_url: str, depth: Optional[int] = None, ensure_commit: Optional[str] = None) -> str:
        """
        캐시된 클론을 반환하거나 새로 클론합니다.

        Args:
            repo_url: 원격 저장소 URL
            depth: clone depth (None=shallow clone with depth=50, 0=full history)
            ensure_commit: 특정 커밋이 필요한 경우 (없으면 fetch)

        Returns:
            str: 로컬 저장소 경로
        """
        cache_key = self._get_cache_key(repo_url)
        now = datetime.now()

        # 이미 캐시된 경우
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            cached_path = entry['path']
            created_at = datetime.fromisoformat(entry['created_at'])

            # 만료 확인
            if now - created_at > timedelta(days=self._expire_days):
                logger.info(f"Cache expired for {repo_url}, re-cloning...")
                self._invalidate_cache(cache_key)
            else:
                # 캐시된 경로가 유효한지 확인
                if os.path.exists(cached_path):
                    try:
                        # depth 요청이 있고 기존보다 깊게 필요한 경우
                        if depth and depth > 50:  # 기본 shallow depth보다 크면
                            logger.info(f"Fetching more commits (depth={depth})...")
                            self._add_safe_directory(cached_path)
                            repo = git.Repo(cached_path)
                            origin = repo.remotes.origin
                            # deepen fetch
                            origin.fetch(depth=depth)
                            repo.close()
                            logger.info(f"✓ Fetched more commits: {cached_path}")

                        # 특정 커밋이 필요한 경우 확인
                        if ensure_commit:
                            if self._ensure_commit_exists(cached_path, repo_url, ensure_commit):
                                logger.info(f"✓ Cache hit with commit {ensure_commit[:8]}: {cached_path}")
                                return cached_path
                            else:
                                # 커밋 fetch 시도
                                logger.warning(f"Commit {ensure_commit[:8]} not found, will fetch")

                        # 이 저장소만 검증 및 업데이트
                        if self._validate_single_repo(cache_key):
                            logger.info(f"✓ Cache hit and updated: {cached_path}")
                            return cached_path
                        else:
                            # 검증 실패 시 재클론
                            logger.warning(f"Cache validation failed, will re-clone")
                            self._invalidate_cache(cache_key)

                    except Exception as e:
                        logger.warning(f"Cached repo invalid, will re-clone: {e}")
                        # 캐시 무효화
                        self._invalidate_cache(cache_key)

        # 새로 클론
        logger.info(f"Cache miss, cloning: {repo_url}")
        local_path = os.path.join(self._cache_dir, cache_key)

        try:
            # 디렉토리가 이미 존재하면 git pull 시도
            if os.path.exists(local_path):
                logger.info(f"Directory already exists: {local_path}")

                try:
                    # Git 저장소인지 확인하고 pull 시도
                    logger.info(f"Attempting to use existing repo and pull...")

                    # safe.directory 설정 (Azure 환경에서 필요)
                    self._add_safe_directory(local_path)

                    existing_repo = git.Repo(local_path)

                    # remote origin 확인
                    if 'origin' in [remote.name for remote in existing_repo.remotes]:
                        origin = existing_repo.remotes.origin

                        # fetch 및 reset (전체 히스토리)
                        logger.info(f"Fetching latest changes (full history)...")
                        origin.fetch()
                        existing_repo.git.reset('--hard', 'origin/HEAD')

                        logger.info(f"✓ Successfully updated existing repository")

                        # 캐시 메타데이터 업데이트
                        now = datetime.now()
                        self._cache[cache_key] = {
                            'url': repo_url,
                            'path': local_path,
                            'created_at': now.isoformat(),
                            'last_accessed': now.isoformat(),
                            'clone_depth': depth
                        }
                        self._save_cache_metadata()

                        return local_path
                    else:
                        logger.warning(f"No 'origin' remote found, will re-clone")
                        raise git.exc.GitCommandError('fetch', 'No origin remote')

                except (git.exc.InvalidGitRepositoryError, git.exc.GitCommandError) as e:
                    logger.warning(f"Cannot use existing directory ({type(e).__name__}), removing and re-cloning...")

                    # Git 저장소 먼저 닫기
                    try:
                        existing_repo.close()
                        del existing_repo
                    except Exception as close_err:
                        logger.debug(f"Could not close repo: {close_err}")

                    # 강력한 삭제 시도
                    self._force_remove_directory(local_path)

                    # 삭제 확인 (여러 번 재시도)
                    max_check_attempts = 5
                    for check_attempt in range(max_check_attempts):
                        if not os.path.exists(local_path):
                            logger.info(f"✓ Directory removal confirmed after {check_attempt + 1} checks")
                            break

                        if check_attempt < max_check_attempts - 1:
                            logger.debug(f"Directory still exists, waiting... (attempt {check_attempt + 1}/{max_check_attempts})")
                            time.sleep(0.5)
                    else:
                        # 모든 재시도 실패
                        raise Exception(f"Failed to remove directory completely: {local_path}")

            # 새로 클론
            logger.info(f"Cloning fresh repository (full history)...")
            logger.warning(f"⚠️ Large repository detected. This may take several minutes...")

            # Windows에서 긴 경로 지원 설정
            try:
                import subprocess
                # Git 글로벌 설정에서 longpaths 활성화
                subprocess.run(['git', 'config', '--global', 'core.longpaths', 'true'],
                             capture_output=True, check=False)
                logger.debug("Enabled Git longpaths support")
            except Exception as e:
                logger.debug(f"Could not set git longpaths: {e}")

            # 진행 상황 콜백
            class CloneProgress(git.RemoteProgress):
                def __init__(self):
                    super().__init__()
                    self.last_log_time = time.time()
                    self.message_obj = None
                    self.current_stage = None
                    self.stage_start_time = time.time()

                    # Chainlit 사용 가능한지 확인
                    try:
                        import chainlit as cl
                        self.cl = cl
                        # 현재 Chainlit 컨텍스트가 있는지 확인
                        if hasattr(cl.context, 'session') and cl.context.session:
                            self.use_chainlit = True
                        else:
                            self.use_chainlit = False
                    except:
                        self.cl = None
                        self.use_chainlit = False

                def _get_stage_name(self, op_code):
                    """작업 코드에서 단계 이름 추출"""
                    if op_code & self.COUNTING:
                        return "Counting objects"
                    elif op_code & self.COMPRESSING:
                        return "Compressing objects"
                    elif op_code & self.RECEIVING:
                        return "Receiving objects"
                    elif op_code & self.RESOLVING:
                        return "Resolving deltas"
                    elif op_code & self.FINDING_SOURCES:
                        return "Finding sources"
                    elif op_code & self.CHECKING_OUT:
                        return "Checking out files"
                    else:
                        return "Processing"

                def update(self, op_code, cur_count, max_count=None, message=''):
                    # 현재 단계 확인
                    stage = self._get_stage_name(op_code)

                    # 단계가 변경되면 로그
                    if stage != self.current_stage:
                        if self.current_stage:
                            elapsed = time.time() - self.stage_start_time
                            logger.info(f"✓ {self.current_stage} completed in {elapsed:.1f}s")
                        self.current_stage = stage
                        self.stage_start_time = time.time()
                        logger.info(f"▶ {stage}...")

                    # 5초마다 진행 상황 로그
                    now = time.time()
                    if now - self.last_log_time >= 5:
                        if max_count and max_count > 0:
                            percentage = (cur_count / max_count * 100)
                            msg = f"  🔄 {stage}: {percentage:.1f}% ({cur_count:,}/{max_count:,})"
                        else:
                            msg = f"  🔄 {stage}: {cur_count:,} items"

                        logger.info(msg)

                        # Chainlit UI에도 표시
                        if self.use_chainlit and self.cl:
                            try:
                                import asyncio

                                async def send_or_update():
                                    if self.message_obj is None:
                                        # 첫 메시지 생성
                                        self.message_obj = await self.cl.Message(
                                            content=msg,
                                            author="System"
                                        ).send()
                                    else:
                                        # 기존 메시지 업데이트
                                        self.message_obj.content = msg
                                        await self.message_obj.update()

                                # 이벤트 루프에서 실행
                                try:
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        # 이미 실행 중인 루프에서는 task 생성
                                        asyncio.create_task(send_or_update())
                                    else:
                                        # 새 루프 실행
                                        asyncio.run(send_or_update())
                                except:
                                    # 동기 방식으로 시도
                                    pass
                            except Exception as e:
                                logger.debug(f"Failed to send Chainlit message: {e}")

                        self.last_log_time = now

            # depth 설정 (기본값: shallow clone)
            if depth is None:
                # 기본: shallow clone (depth=50)
                clone_depth = 50
                logger.info(f"Using shallow clone (depth={clone_depth})")
            elif depth == 0:
                # 전체 히스토리
                clone_depth = None
                logger.info("Using full history clone")
            else:
                clone_depth = depth
                logger.info(f"Using custom depth: {clone_depth}")

            clone_kwargs = {
                'single_branch': True,
                'progress': CloneProgress()  # 진행 상황 추가
            }

            if clone_depth:
                clone_kwargs['depth'] = clone_depth

            logger.info(f"Starting clone of {repo_url}...")

            # Chainlit UI에 시작 메시지 전송
            try:
                import chainlit as cl
                if hasattr(cl.context, 'session') and cl.context.session:
                    import asyncio
                    async def send_start_msg():
                        await cl.Message(
                            content=f"🔄 저장소 클론 시작: {repo_url}\n⚠️ 큰 저장소는 수 분이 소요될 수 있습니다.",
                            author="System"
                        ).send()

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(send_start_msg())
                        else:
                            asyncio.run(send_start_msg())
                    except:
                        pass
            except:
                pass

            start_time = time.time()

            repo = git.Repo.clone_from(
                repo_url,
                local_path,
                **clone_kwargs
            )

            elapsed = time.time() - start_time
            logger.info(f"✓ Clone completed in {elapsed:.1f} seconds")

            # Chainlit UI에 완료 메시지 전송
            try:
                import chainlit as cl
                if hasattr(cl.context, 'session') and cl.context.session:
                    import asyncio
                    async def send_complete_msg():
                        await cl.Message(
                            content=f"✅ 저장소 클론 완료! ({elapsed:.1f}초)",
                            author="System"
                        ).send()

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(send_complete_msg())
                        else:
                            asyncio.run(send_complete_msg())
                    except:
                        pass
            except:
                pass

            # Azure 환경에서 safe.directory 설정 (클론 직후)
            self._add_safe_directory(local_path)

            # 캐시 메타데이터 저장
            self._cache[cache_key] = {
                'url': repo_url,
                'path': local_path,
                'created_at': now.isoformat(),
                'last_accessed': now.isoformat()
            }
            self._save_cache_metadata()

            logger.info(f"✓ Cloned and cached: {local_path}")

            return local_path

        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")

            # 파일명이 너무 긴 경우 특별 처리
            error_msg = str(e)
            if 'Filename too long' in error_msg or 'unable to create file' in error_msg:
                logger.error("=" * 60)
                logger.error("Git Clone 실패: 파일 경로가 너무 깁니다")
                logger.error("=" * 60)
                logger.error(f"저장소: {repo_url}")
                logger.error("\n해결 방법:")
                logger.error("1. 관리자 권한으로 PowerShell 실행")
                logger.error("2. 다음 명령 실행: git config --system core.longpaths true")
                logger.error("3. 또는 Windows 레지스트리에서 긴 경로 활성화:")
                logger.error("   HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem")
                logger.error("   LongPathsEnabled = 1 (DWORD)")
                logger.error("4. 프로그램 재시작")
                logger.error("=" * 60)

                # 실패한 디렉토리 정리
                if os.path.exists(local_path):
                    try:
                        import stat
                        def remove_readonly(func, path, _):
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        shutil.rmtree(local_path, onerror=remove_readonly)
                    except:
                        pass

                raise Exception(
                    f"파일 경로가 너무 깁니다. Windows에서 긴 경로 지원을 활성화해야 합니다. "
                    f"관리자 권한으로 'git config --system core.longpaths true' 실행 후 재시도하세요."
                ) from e

            # 실패 시 디렉토리 정리
            if os.path.exists(local_path):
                shutil.rmtree(local_path, ignore_errors=True)
            raise

    def _invalidate_cache(self, cache_key: str):
        """캐시 무효화"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            cached_path = entry['path']

            # 경로 정규화 및 검증
            cached_path = self._normalize_cache_path(cached_path, cache_key)

            if os.path.exists(cached_path):
                # 1단계: Git 저장소 닫기
                try:
                    repo = git.Repo(cached_path)
                    repo.close()
                    del repo
                    logger.debug(f"Closed Git repo: {cached_path}")
                except Exception as e:
                    logger.debug(f"Could not close repo (may not be valid): {e}")

                # 2단계: 강력한 삭제
                try:
                    self._force_remove_directory(cached_path)
                except Exception as e:
                    logger.error(f"Failed to remove cached repo: {e}")

            del self._cache[cache_key]
            self._save_cache_metadata()

    def clear_all(self):
        """모든 캐시 정리"""
        logger.info("Clearing all cached repositories...")

        for cache_key in list(self._cache.keys()):
            self._invalidate_cache(cache_key)

        if self._cache_dir and os.path.exists(self._cache_dir):
            try:
                shutil.rmtree(self._cache_dir, ignore_errors=True)
                logger.info(f"✓ Cleared cache directory: {self._cache_dir}")
            except Exception as e:
                logger.warning(f"Failed to clear cache directory: {e}")

        self._cache.clear()
        self._save_cache_metadata()

    def get_cache_info(self) -> Dict:
        """캐시 정보 반환"""
        info = {
            "cache_dir": self._cache_dir or "",
            "cache_file": self._cache_file or "",
            "cached_repos": len(self._cache),
            "expire_days": self._expire_days,
            "repos": []
        }

        now = datetime.now()
        for cache_key, entry in self._cache.items():
            created_at = datetime.fromisoformat(entry['created_at'])
            age_days = (now - created_at).days

            info["repos"].append({
                "url": entry['url'],
                "cache_key": cache_key,
                "age_days": age_days,
                "is_expired": age_days > self._expire_days
            })

        return info

    def __del__(self):
        """소멸자 - 메타데이터 저장 (캐시 디렉토리는 유지)"""
        # 프로그램 종료 시 메타데이터만 저장, 캐시 디렉토리는 유지
        try:
            # json과 open이 아직 사용 가능한지 확인
            if hasattr(self, '_cache_file') and self._cache_file:
                import builtins
                if hasattr(builtins, 'open'):
                    self._save_cache_metadata()
        except Exception:
            # 프로그램 종료 시 에러는 무시
            pass

