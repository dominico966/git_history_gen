"""
Git 저장소에서 커밋 히스토리를 추출하는 문서 생성기
"""

import git
from typing import List, Dict, Optional
from collections import defaultdict
import logging
import asyncio
import tempfile
import shutil
import os
import json
import hashlib
from pathlib import Path
from src.repo_cache import RepoCloneCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Git 저장소에서 커밋 정보를 추출합니다."""

    def __init__(self, repo_path: str):
        """
        Args:
            repo_path: Git 저장소 경로 또는 URL (https://github.com/...)

        Raises:
            git.exc.InvalidGitRepositoryError: 유효한 Git 저장소가 아닌 경우
        """
        self.temp_dir = None
        self.is_remote = False
        self.use_cache = False  # 캐시 사용 여부
        self.repo_path = repo_path

        # 커밋 메타데이터 캐시 초기화
        self._setup_commit_cache()

        try:
            # URL인지 확인
            if repo_path.startswith(('http://', 'https://', 'git@', 'ssh://')):
                self.is_remote = True
                self.use_cache = True
                logger.info(f"Detected remote repository: {repo_path}")

                # 캐시에서 가져오거나 새로 클론 (shallow clone - depth=50)
                cache = RepoCloneCache()
                cached_path = cache.get_or_clone(repo_path, depth=None)  # None = shallow clone

                # 캐시된 경로 사용 (temp_dir는 설정하지 않음 - 캐시 매니저가 관리)
                self.repo = git.Repo(cached_path)
                self.cached_path = cached_path
                self.repo_url = repo_path
                logger.info(f"Using repository from cache: {cached_path}")
            else:
                # 로컬 저장소
                self.repo = git.Repo(repo_path)
                self.cached_path = None
                self.repo_url = None
                logger.info(f"Initialized Git repository: {repo_path}")

        except git.exc.InvalidGitRepositoryError as e:
            logger.error(f"Invalid Git repository: {repo_path}")
            self._cleanup()
            raise
        except git.exc.GitCommandError as e:
            logger.error(f"Git command failed: {e}")
            self._cleanup()
            raise
        except Exception as e:
            logger.error(f"Failed to initialize repository: {e}")
            self._cleanup()
            raise

    def _setup_commit_cache(self):
        """커밋 메타데이터 캐시 디렉토리 설정"""
        # 저장소별 캐시 키 생성
        repo_hash = hashlib.md5(self.repo_path.encode()).hexdigest()[:12]

        # 캐시 루트 디렉토리 결정
        if 'REPO_CACHE_DIR' in os.environ:
            cache_root = Path(os.environ['REPO_CACHE_DIR'])
        elif os.path.exists('/home/site/wwwroot'):
            home_dir = os.environ.get('HOME', '/home')
            cache_root = Path(home_dir) / '.cache'
        elif os.name == 'posix' and 'HOME' in os.environ:
            cache_root = Path(os.environ['HOME']) / '.cache' / 'git_history_gen'
        elif os.name == 'posix':
            cache_root = Path(tempfile.gettempdir()) / 'git_history_gen_cache'
        else:
            project_root = Path(__file__).parent.parent.resolve()
            cache_root = project_root / '.cache'

        # 커밋 메타데이터 캐시 디렉토리
        self.commit_cache_dir = cache_root / 'commits' / repo_hash
        self.commit_cache_dir.mkdir(parents=True, exist_ok=True)
        self.commit_cache_file = self.commit_cache_dir / 'commits.json'

        # 캐시 로드
        self._commit_cache = {}
        if self.commit_cache_file.exists():
            try:
                with open(self.commit_cache_file, 'r', encoding='utf-8') as f:
                    self._commit_cache = json.load(f)
                logger.info(f"Loaded {len(self._commit_cache)} cached commits for {repo_hash}")
            except Exception as e:
                logger.warning(f"Failed to load commit cache: {e}")
                self._commit_cache = {}

    def _save_commit_cache(self):
        """커밋 메타데이터 캐시 저장"""
        try:
            with open(self.commit_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._commit_cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self._commit_cache)} commits to cache")
        except Exception as e:
            logger.error(f"Failed to save commit cache: {e}")

    def _get_cached_commit(self, commit_sha: str) -> Optional[Dict]:
        """캐시된 커밋 메타데이터 가져오기"""
        return self._commit_cache.get(commit_sha)

    def _cache_commit(self, commit_sha: str, commit_data: Dict):
        """커밋 메타데이터 캐시"""
        self._commit_cache[commit_sha] = commit_data

    def _cleanup(self):
        """임시 디렉토리 정리 (캐시 사용 시에는 정리하지 않음)"""
        # 커밋 캐시 저장
        if hasattr(self, '_commit_cache') and self._commit_cache:
            self._save_commit_cache()

        # Git 저장소 닫기 (파일 핸들 해제)
        try:
            if hasattr(self, 'repo') and self.repo:
                self.repo.close()
                logger.debug("Git repository closed")
        except Exception as e:
            logger.debug(f"Failed to close repo: {e}")

        # 임시 디렉토리 정리 (캐시 미사용 시만)
        if self.temp_dir and self.is_remote and not self.use_cache:
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")

    def __del__(self):
        """소멸자 - 임시 디렉토리 정리 (캐시 사용 시에는 정리하지 않음)"""
        self._cleanup()

    def get_commits(
        self,
        limit: Optional[int] = 10,
        branch: str = "HEAD",
        since: Optional[str] = None,
        until: Optional[str] = None,
        skip: int = 0
    ) -> List[Dict]:
        """
        커밋 히스토리를 추출합니다.

        Args:
            limit: 추출할 최대 커밋 수 (None이면 전체, 기본값: 10)
            branch: 추출할 브랜치 (기본값: HEAD)
            since: 시작 날짜 (ISO 8601 형식, 예: '2024-01-01')
            until: 종료 날짜 (ISO 8601 형식, 예: '2024-12-31')
            skip: HEAD부터 건너뛸 커밋 수 (기본값: 0)

        Returns:
            List[Dict]: 커밋 정보 리스트 (변경 문맥 및 함수 분석 포함)
        """
        try:
            commits = []
            new_commits_count = 0
            cached_commits_count = 0

            logger.info(f"Extracting commits from {branch} (limit: {limit}, since: {since}, until: {until}, skip: {skip})")

            # 날짜 범위 또는 skip이 지정된 경우 더 깊게 fetch 필요
            if self.is_remote and self.cached_path and self.repo_url:
                fetch_depth = None  # 기본값 (fetch 안 함)

                if skip > 0:
                    # skip offset이 있으면 충분한 depth 필요
                    fetch_depth = skip + (limit if limit else 100)
                    logger.info(f"Skip offset {skip} detected, ensuring depth >= {fetch_depth}")
                elif since or until:
                    # 날짜 범위가 지정된 경우, 충분히 깊게 fetch (최대 1000개)
                    fetch_depth = 1000
                    logger.info(f"Date range specified, fetching deeper (depth={fetch_depth})")

                if fetch_depth:
                    from src.repo_cache import RepoCloneCache
                    cache = RepoCloneCache()
                    # 필요한 만큼 깊게 fetch
                    cache.get_or_clone(self.repo_url, depth=fetch_depth)
                    # 저장소 reload
                    self.repo = git.Repo(self.cached_path)

            # 날짜 필터링 옵션 설정
            kwargs = {'max_count': limit} if limit else {}
            if since:
                kwargs['since'] = since
            if until:
                kwargs['until'] = until
            if skip > 0:
                kwargs['skip'] = skip

            commit_list = list(self.repo.iter_commits(branch, **kwargs))

            for idx, commit in enumerate(commit_list):
                try:
                    commit_sha = commit.hexsha

                    # 캐시에서 먼저 확인
                    cached_data = self._get_cached_commit(commit_sha)
                    if cached_data:
                        commits.append(cached_data)
                        cached_commits_count += 1
                        logger.debug(f"Using cached commit: {commit_sha[:8]}")
                        continue

                    # 캐시에 없으면 새로 생성
                    commit_data = {
                        "id": commit_sha,
                        "message": commit.message.strip(),
                        "author": commit.author.name,
                        "author_email": commit.author.email,
                        "date": commit.committed_datetime.isoformat(),
                        "parents": [p.hexsha for p in commit.parents],
                        "files": self.get_changed_files(commit)
                    }

                    # 커밋 간 변경사항 문맥 추가
                    commit_data["change_context"] = self.get_change_context(commit)

                    # 함수/기능 분석 메타데이터 추가
                    commit_data["function_analysis"] = self.analyze_functions_in_commit(commit)

                    # 이전 커밋과의 관계 분석 (첫 커밋이 아닌 경우)
                    if idx < len(commit_list) - 1:
                        previous_commit = commit_list[idx + 1]
                        commit_data["relation_to_previous"] = self.get_commit_relation(
                            commit, previous_commit
                        )
                    else:
                        commit_data["relation_to_previous"] = None

                    # 캐시에 저장
                    self._cache_commit(commit_sha, commit_data)
                    commits.append(commit_data)
                    new_commits_count += 1

                except git.exc.GitCommandError as e:
                    # shallow clone에서 커밋이 없는 경우 더 fetch
                    if 'does not have' in str(e) or 'unknown revision' in str(e):
                        logger.warning(f"Commit not in shallow clone, fetching more history...")
                        if self.is_remote and self.cached_path and self.repo_url:
                            from src.repo_cache import RepoCloneCache
                            cache = RepoCloneCache()
                            # 더 깊게 fetch (depth=1000)
                            cache.get_or_clone(self.repo_url, depth=1000, ensure_commit=commit.hexsha)
                            # 재시도
                            continue
                    logger.warning(f"Failed to process commit {commit.hexsha[:8]}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to process commit {commit.hexsha[:8]}: {e}")
                    continue

            # 주기적으로 캐시 저장 (메모리 절약)
            if new_commits_count > 0:
                self._save_commit_cache()

            logger.info(f"✓ Extracted {len(commits)} commits (cached: {cached_commits_count}, new: {new_commits_count})")
            return commits

        except Exception as e:
            logger.error(f"Failed to get commits: {e}")
            raise

    def get_changed_files(self, commit: git.Commit, context_lines: int = 50) -> List[Dict]:
        """
        커밋에서 변경된 파일 목록과 변경 통계를 추출합니다.

        Args:
            commit: Git 커밋 객체
            context_lines: 변경 부분 주변 컨텍스트 라인 수 (기본값: 50)

        Returns:
            List[Dict]: 변경된 파일 정보 리스트 (주변 컨텍스트 포함)
        """
        try:
            files = []

            # 부모가 있으면 부모와 비교, 없으면 초기 커밋
            if commit.parents:
                diff = commit.parents[0].diff(commit, create_patch=True)
            else:
                diff = commit.diff(git.NULL_TREE, create_patch=True)

            for item in diff:
                try:
                    file_path = item.a_path if item.a_path else item.b_path

                    # 라인 수 계산 및 변경 컨텍스트 추출
                    lines_added = 0
                    lines_deleted = 0
                    change_context = []  # 변경 부분의 주변 컨텍스트

                    if item.diff:
                        try:
                            # UTF-8 디코딩 시도, 실패 시 latin-1로 폴백
                            try:
                                diff_text = item.diff.decode('utf-8') if isinstance(item.diff, bytes) else item.diff
                            except (UnicodeDecodeError, AttributeError) as ude:
                                logger.debug(f"UTF-8 decode failed for {file_path}, trying latin-1: {ude}")
                                diff_text = item.diff.decode('latin-1', errors='ignore') if isinstance(item.diff, bytes) else str(item.diff)

                            # diff를 라인별로 분석
                            diff_lines = diff_text.split('\n')

                            # 변경된 부분 찾기 및 컨텍스트 추출
                            change_blocks = []
                            current_block = []
                            in_change = False
                            context_before = []

                            for i, line in enumerate(diff_lines):
                                # 변경 라인 카운트
                                if line.startswith('+') and not line.startswith('+++'):
                                    lines_added += 1
                                    in_change = True
                                    current_block.append(line)
                                elif line.startswith('-') and not line.startswith('---'):
                                    lines_deleted += 1
                                    in_change = True
                                    current_block.append(line)
                                elif line.startswith(' ') or line.startswith('@@'):
                                    # 컨텍스트 라인
                                    if in_change:
                                        # 변경 후 컨텍스트
                                        current_block.append(line)
                                        if len(current_block) >= context_lines * 2:
                                            # 블록 완성
                                            change_blocks.append({
                                                'lines': current_block[:context_lines * 2],
                                                'start_line': i - len(current_block) + 1
                                            })
                                            current_block = []
                                            in_change = False
                                    else:
                                        # 변경 전 컨텍스트 누적
                                        context_before.append(line)
                                        if len(context_before) > context_lines:
                                            context_before.pop(0)

                                        # 컨텍스트를 current_block에 추가
                                        if context_before and not current_block:
                                            current_block = context_before[:]

                            # 마지막 블록 처리
                            if current_block and in_change:
                                change_blocks.append({
                                    'lines': current_block[:context_lines * 2],
                                    'start_line': len(diff_lines) - len(current_block)
                                })

                            # 변경 컨텍스트 포맷팅 (최대 3개 블록만)
                            for block in change_blocks[:3]:
                                context_snippet = '\n'.join(block['lines'][:100])  # 최대 100라인
                                if len(context_snippet) > 1000:
                                    context_snippet = context_snippet[:1000] + '\n...(truncated)'
                                change_context.append({
                                    'start_line': block['start_line'],
                                    'snippet': context_snippet
                                })

                        except Exception as e:
                            logger.warning(f"Failed to decode diff for {file_path}: {type(e).__name__} - {str(e)}")
                            pass

                    file_info = {
                        "file": file_path,
                        "change_type": item.change_type,
                        "lines_added": lines_added,
                        "lines_deleted": lines_deleted
                    }

                    # 변경 컨텍스트가 있으면 추가
                    if change_context:
                        file_info["change_context"] = change_context

                    files.append(file_info)

                except Exception as e:
                    logger.debug(f"Failed to process file in commit: {e}")
                    continue

            return files

        except Exception as e:
            logger.warning(f"Failed to get changed files: {e}")
            return []

    async def get_commits_async(
        self,
        limit: Optional[int] = 10,
        branch: str = "HEAD",
        since: Optional[str] = None,
        until: Optional[str] = None,
        skip: int = 0
    ) -> List[Dict]:
        """
        비동기적으로 커밋 히스토리를 추출합니다.

        Args:
            limit: 추출할 최대 커밋 수
            branch: 추출할 브랜치
            since: 시작 날짜
            until: 종료 날짜
            skip: HEAD부터 건너뛸 커밋 수

        Returns:
            List[Dict]: 커밋 정보 리스트
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_commits, limit, branch, since, until, skip)

    def get_file_history(self, file_path: str, limit: Optional[int] = None) -> List[Dict]:
        """
        특정 파일의 변경 히스토리를 추출합니다.

        Args:
            file_path: 파일 경로
            limit: 추출할 최대 커밋 수

        Returns:
            List[Dict]: 해당 파일을 변경한 커밋 리스트
        """
        try:
            commits = []

            for commit in self.repo.iter_commits(paths=file_path, max_count=limit):
                commits.append({
                    "id": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat()
                })

            logger.info(f"✓ Found {len(commits)} commits for file: {file_path}")
            return commits

        except Exception as e:
            logger.error(f"Failed to get file history: {e}")
            return []

    def close(self) -> None:
        """저장소를 닫습니다."""
        try:
            if hasattr(self, 'repo') and self.repo:
                self.repo.close()
                logger.debug("Repository closed")
        except Exception as e:
            logger.warning(f"Failed to close repository: {e}")

    def get_change_context(self, commit: git.Commit) -> Dict:
        """
        커밋의 변경사항에 대한 문맥을 추출합니다.

        Args:
            commit: Git 커밋 객체

        Returns:
            Dict: 변경 문맥 정보
        """
        try:
            context = {
                "summary": "",
                "impact_scope": [],
                "change_types": [],
                "file_categories": {}
            }

            if not commit.parents:
                context["summary"] = "Initial commit - 프로젝트 시작"
                return context

            # 변경된 파일 분석
            diff = commit.parents[0].diff(commit)

            change_types_set = set()
            file_categories_dict = defaultdict(int)

            for item in diff:
                file_path = item.a_path if item.a_path else item.b_path

                # 변경 타입 수집
                change_types_set.add(item.change_type)

                # 파일 카테고리 분류
                if file_path:
                    if '/' in file_path:
                        category = file_path.split('/')[0]
                        file_categories_dict[category] += 1

                    # 영향 범위 파악
                    if any(ext in file_path for ext in ['.py', '.js', '.ts', '.java', '.go', '.rs']):
                        context["impact_scope"].append(f"Source: {file_path}")
                    elif any(ext in file_path for ext in ['.md', '.txt', '.rst']):
                        context["impact_scope"].append(f"Documentation: {file_path}")
                    elif any(ext in file_path for ext in ['.json', '.yaml', '.yml', '.toml', '.xml']):
                        context["impact_scope"].append(f"Configuration: {file_path}")
                    elif any(ext in file_path for ext in ['.test.', 'test_', '_test.']):
                        context["impact_scope"].append(f"Test: {file_path}")

            # 요약 생성
            change_type_names = {
                'A': '추가', 'D': '삭제', 'M': '수정', 'R': '이름변경', 'T': '타입변경'
            }
            types_str = ', '.join([change_type_names.get(t, t) for t in change_types_set])

            total_files = sum(file_categories_dict.values())
            context["summary"] = f"{total_files}개 파일 {types_str}"

            # set을 list로, defaultdict를 dict로 변환 (JSON 직렬화 가능하도록)
            context["change_types"] = list(change_types_set)
            context["file_categories"] = dict(file_categories_dict)

            return context

        except Exception as e:
            logger.warning(f"Failed to get change context: {e}")
            return {
                "summary": "분석 실패",
                "impact_scope": [],
                "change_types": [],
                "file_categories": {}
            }

    def analyze_functions_in_commit(self, commit: git.Commit) -> Dict:
        """
        커밋에서 수정된 함수/클래스를 분석합니다.

        Args:
            commit: Git 커밋 객체

        Returns:
            Dict: 함수 분석 정보
        """
        try:
            analysis = {
                "modified_functions": [],
                "modified_classes": [],
                "added_functions": [],
                "removed_functions": [],
                "code_complexity_hint": "medium"
            }

            if not commit.parents:
                return analysis

            diff = commit.parents[0].diff(commit, create_patch=True)

            for item in diff:
                file_path = item.a_path if item.a_path else item.b_path

                # Python 파일만 상세 분석
                if file_path and file_path.endswith('.py'):
                    if item.diff:
                        try:
                            # UTF-8 디코딩 시도, 실패 시 latin-1로 폴백
                            try:
                                diff_text = item.diff.decode('utf-8')
                            except UnicodeDecodeError as ude:
                                logger.debug(f"UTF-8 decode failed for {file_path}, trying latin-1: {ude}")
                                diff_text = item.diff.decode('latin-1', errors='ignore')

                            # 함수 정의 패턴 찾기
                            import re

                            # 추가된 함수
                            added_funcs = re.findall(r'^\+\s*def\s+(\w+)\s*\(', diff_text, re.MULTILINE)
                            if added_funcs:
                                analysis["added_functions"].extend([
                                    {"name": f, "file": file_path} for f in added_funcs
                                ])

                            # 제거된 함수
                            removed_funcs = re.findall(r'^-\s*def\s+(\w+)\s*\(', diff_text, re.MULTILINE)
                            if removed_funcs:
                                analysis["removed_functions"].extend([
                                    {"name": f, "file": file_path} for f in removed_funcs
                                ])

                            # 클래스 변경
                            modified_classes = re.findall(r'^\+\s*class\s+(\w+)', diff_text, re.MULTILINE)
                            if modified_classes:
                                analysis["modified_classes"].extend([
                                    {"name": c, "file": file_path} for c in modified_classes
                                ])

                            # 수정된 함수 (diff 컨텍스트에서 찾기)
                            # @@ ... @@ 근처의 함수명 추출
                            context_funcs = re.findall(
                                r'@@.*?@@\s+(?:def|class)\s+(\w+)',
                                diff_text,
                                re.MULTILINE
                            )
                            if context_funcs:
                                analysis["modified_functions"].extend([
                                    {"name": f, "file": file_path} for f in context_funcs
                                ])

                            # 복잡도 힌트 (변경 라인 수 기반)
                            lines_changed = diff_text.count('\n+') + diff_text.count('\n-')
                            if lines_changed > 100:
                                analysis["code_complexity_hint"] = "high"
                            elif lines_changed < 20:
                                analysis["code_complexity_hint"] = "low"

                        except Exception as e:
                            logger.warning(f"Failed to analyze functions in {file_path}: {type(e).__name__} - {str(e)}")
                            pass

            return analysis

        except Exception as e:
            logger.warning(f"Failed to analyze functions: {e}")
            return {
                "modified_functions": [],
                "modified_classes": [],
                "added_functions": [],
                "removed_functions": [],
                "code_complexity_hint": "unknown"
            }

    def get_commit_relation(self, current: git.Commit, previous: git.Commit) -> Dict:
        """
        현재 커밋과 이전 커밋의 관계를 분석합니다.

        Args:
            current: 현재 커밋
            previous: 이전 커밋

        Returns:
            Dict: 커밋 간 관계 정보
        """
        try:
            relation = {
                "time_delta_seconds": 0,
                "same_author": False,
                "common_files": [],
                "relationship_type": "sequential"
            }

            # 시간 차이
            time_diff = current.committed_datetime - previous.committed_datetime
            relation["time_delta_seconds"] = int(time_diff.total_seconds())

            # 동일 작성자 확인
            relation["same_author"] = (current.author.email == previous.author.email)

            # 공통 파일 찾기
            current_files = {f["file"] for f in self.get_changed_files(current)}
            previous_files = {f["file"] for f in self.get_changed_files(previous)}
            relation["common_files"] = list(current_files & previous_files)

            # 관계 타입 결정
            if relation["same_author"] and relation["time_delta_seconds"] < 3600:  # 1시간 이내
                relation["relationship_type"] = "related_work"
            elif len(relation["common_files"]) > 0:
                relation["relationship_type"] = "same_area"
            else:
                relation["relationship_type"] = "independent"

            return relation

        except Exception as e:
            logger.warning(f"Failed to analyze commit relation: {e}")
            return {
                "time_delta_seconds": 0,
                "same_author": False,
                "common_files": [],
                "relationship_type": "unknown"
            }
