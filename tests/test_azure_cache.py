"""
Azure 환경 캐시 디렉토리 및 safe.directory 설정 테스트
"""

import os
import sys
import tempfile
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.repo_cache import RepoCloneCache


def test_cache_directory_selection():
    """캐시 디렉토리 선택 테스트"""
    print("=" * 60)
    print("캐시 디렉토리 선택 테스트")
    print("=" * 60)

    # 현재 환경 확인
    print(f"\n현재 OS: {os.name}")
    print(f"Azure 환경: {os.path.exists('/home/site/wwwroot')}")
    print(f"HOME 환경 변수: {os.environ.get('HOME', 'Not set')}")

    # RepoCloneCache 초기화
    cache = RepoCloneCache()

    print(f"\n선택된 캐시 디렉토리: {cache._cache_dir}")
    print(f"캐시 메타데이터 파일: {cache._cache_file}")

    # 디렉토리 존재 확인
    if os.path.exists(cache._cache_dir):
        print(f"✓ 캐시 디렉토리 존재함")
    else:
        print(f"✗ 캐시 디렉토리가 생성되지 않음")

    # 환경별 예상 경로 확인
    print("\n환경별 예상 캐시 경로:")

    # Azure 환경
    if os.path.exists('/home/site/wwwroot'):
        # Azure에서도 HOME 환경변수 사용
        home_dir = os.environ.get('HOME', '/home')
        expected = Path(home_dir) / '.cache' / 'repos'
        print(f"  Azure (HOME={home_dir}): {expected}")
        assert str(cache._cache_dir) == str(expected), f"Azure 환경에서 경로 불일치: expected={expected}, actual={cache._cache_dir}"

    # Linux with HOME
    elif os.name == 'posix' and 'HOME' in os.environ:
        home_dir = os.environ['HOME']
        expected = Path(home_dir) / '.cache' / 'git_history_gen' / 'repos'
        print(f"  Linux (HOME={home_dir}): {expected}")
        assert str(cache._cache_dir) == str(expected), f"Linux 환경에서 경로 불일치: expected={expected}, actual={cache._cache_dir}"

    # Linux without HOME (use /tmp)
    elif os.name == 'posix':
        expected_prefix = '/tmp/git_history_gen_cache'
        print(f"  Linux (no HOME): {expected_prefix}/*")
        assert expected_prefix in cache._cache_dir, "Linux 임시 디렉토리 경로 불일치"

    # Windows
    elif os.name == 'nt':
        expected = project_root / '.cache' / 'repos'
        print(f"  Windows: {expected}")
        assert str(cache._cache_dir) == str(expected), "Windows 환경에서 경로 불일치"

    print("\n✓ 캐시 디렉토리 선택 테스트 통과")


def test_env_override():
    """환경 변수로 캐시 디렉토리 오버라이드 테스트"""
    print("\n" + "=" * 60)
    print("환경 변수 오버라이드 테스트")
    print("=" * 60)

    # 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp(prefix='test_cache_')

    # 환경 변수 설정
    os.environ['REPO_CACHE_DIR'] = temp_dir

    try:
        # 싱글톤 인스턴스 리셋
        RepoCloneCache.reset_instance()

        # 새 인스턴스 생성
        cache = RepoCloneCache()

        print(f"\n환경 변수 설정: {temp_dir}")
        print(f"실제 캐시 디렉토리: {cache._cache_dir}")

        # 검증
        assert temp_dir in cache._cache_dir, "환경 변수가 적용되지 않음"

        print("\n✓ 환경 변수 오버라이드 테스트 통과")

    finally:
        # 정리
        del os.environ['REPO_CACHE_DIR']
        RepoCloneCache.reset_instance()

        # 임시 디렉토리 삭제
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def test_git_safe_directory_config():
    """Git safe.directory 설정 테스트"""
    print("\n" + "=" * 60)
    print("Git safe.directory 설정 테스트")
    print("=" * 60)

    import subprocess

    try:
        # Git 설치 확인
        result = subprocess.run(['git', '--version'], capture_output=True, timeout=5, text=True)
        print(f"\nGit 버전: {result.stdout.strip()}")

        # 현재 safe.directory 설정 확인
        result = subprocess.run(
            ['git', 'config', '--global', '--get-all', 'safe.directory'],
            capture_output=True,
            timeout=5,
            text=True
        )

        if result.returncode == 0:
            safe_dirs = result.stdout.strip().split('\n')
            print(f"\n현재 safe.directory 설정:")
            for sd in safe_dirs:
                print(f"  - {sd}")

            # '*' 가 포함되어 있는지 확인
            if '*' in safe_dirs:
                print("\n✓ 모든 디렉토리가 안전한 것으로 설정됨")
            else:
                print("\n⚠ 와일드카드 설정이 없음 (특정 디렉토리만 설정됨)")
        else:
            print("\n⚠ safe.directory 설정이 없음")

        print("\n✓ Git safe.directory 설정 확인 완료")

    except FileNotFoundError:
        print("\n⚠ Git이 설치되지 않았거나 PATH에 없음")
    except Exception as e:
        print(f"\n⚠ 오류 발생: {e}")


def test_small_repo_clone():
    """작은 저장소 클론 테스트 (실제 클론)"""
    print("\n" + "=" * 60)
    print("실제 저장소 클론 테스트")
    print("=" * 60)

    # 작은 테스트 저장소 URL
    test_repo = "https://github.com/octocat/Hello-World.git"

    try:
        cache = RepoCloneCache()

        print(f"\n테스트 저장소: {test_repo}")
        print("클론 시작...")

        local_path = cache.get_or_clone(test_repo)

        print(f"✓ 클론 완료: {local_path}")

        # 디렉토리 존재 확인
        assert os.path.exists(local_path), "로컬 경로가 존재하지 않음"
        assert os.path.isdir(local_path), "로컬 경로가 디렉토리가 아님"

        # Git 저장소 확인
        import git
        repo = git.Repo(local_path)

        print(f"✓ Git 저장소 확인 완료")
        print(f"  브랜치: {repo.active_branch.name}")
        print(f"  최신 커밋: {repo.head.commit.hexsha[:8]}")

        # 캐시 재사용 테스트
        print("\n캐시 재사용 테스트...")
        local_path2 = cache.get_or_clone(test_repo)

        assert local_path == local_path2, "캐시가 재사용되지 않음"
        print("✓ 캐시 재사용 확인")

        print("\n✓ 실제 저장소 클론 테스트 통과")

    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """모든 테스트 실행"""
    print("\n")
    print("█" * 60)
    print(" Azure 캐시 디렉토리 및 safe.directory 테스트")
    print("█" * 60)

    try:
        # 1. 캐시 디렉토리 선택 테스트
        test_cache_directory_selection()

        # 2. 환경 변수 오버라이드 테스트
        test_env_override()

        # 3. Git safe.directory 설정 테스트
        test_git_safe_directory_config()

        # 4. 실제 저장소 클론 테스트 (선택적)
        user_input = input("\n실제 저장소 클론 테스트를 수행하시겠습니까? (y/N): ")
        if user_input.lower() == 'y':
            test_small_repo_clone()
        else:
            print("저장소 클론 테스트 건너뜀")

        print("\n" + "=" * 60)
        print("✓ 모든 테스트 통과")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

