"""
디렉토리 삭제 및 재생성 통합 테스트
실제 시나리오: 잘못된 Git 저장소 삭제 후 즉시 재클론
"""

import logging
import sys
import os
import shutil
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.repo_cache import RepoCloneCache


def test_directory_removal_and_recreation():
    """디렉토리 삭제 후 즉시 재생성 테스트"""
    print("\n" + "=" * 60)
    print("디렉토리 삭제 및 재생성 테스트")
    print("=" * 60)

    # 싱글톤 리셋
    RepoCloneCache.reset_instance()
    cache = RepoCloneCache()

    # 테스트용 디렉토리 생성
    test_dir = os.path.join(cache._cache_dir, "test_removal_" + os.urandom(4).hex())

    print(f"\n1. 테스트 디렉토리 생성: {test_dir}")
    os.makedirs(test_dir, exist_ok=True)

    # 더미 파일 생성 (Git 저장소 시뮬레이션)
    test_file = os.path.join(test_dir, "test_file.txt")
    with open(test_file, 'w') as f:
        f.write("test content")

    # 읽기 전용 파일도 추가
    readonly_file = os.path.join(test_dir, "readonly.txt")
    with open(readonly_file, 'w') as f:
        f.write("readonly content")
    os.chmod(readonly_file, 0o444)  # 읽기 전용

    assert os.path.exists(test_dir), "테스트 디렉토리가 생성되지 않았습니다"
    print("✓ 테스트 디렉토리 및 파일 생성 완료")

    # 2. 강제 삭제 시도
    print(f"\n2. 강제 삭제 시도...")
    try:
        cache._force_remove_directory(test_dir)
        print("✓ 삭제 완료")
    except Exception as e:
        print(f"✗ 삭제 실패: {e}")
        raise

    # 3. 삭제 확인
    print(f"\n3. 삭제 확인 (5회 재시도)...")
    import time

    for i in range(5):
        if not os.path.exists(test_dir):
            print(f"✓ 디렉토리가 완전히 삭제되었습니다 (확인 {i + 1}회)")
            break
        print(f"  - 재시도 {i + 1}/5: 디렉토리가 아직 존재합니다, 대기 중...")
        time.sleep(0.5)
    else:
        raise AssertionError(f"디렉토리가 삭제되지 않았습니다: {test_dir}")

    # 4. 동일한 경로에 즉시 재생성 시도
    print(f"\n4. 동일한 경로에 즉시 재생성...")
    try:
        os.makedirs(test_dir, exist_ok=False)
        print("✓ 재생성 성공")
    except FileExistsError:
        print("✗ 재생성 실패: 디렉토리가 아직 존재합니다")
        raise
    except Exception as e:
        print(f"✗ 재생성 실패: {e}")
        raise

    # 5. 정리
    print(f"\n5. 테스트 정리...")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    print("✓ 정리 완료")

    print("\n" + "=" * 60)
    print("테스트 통과! ✓")
    print("=" * 60)


def test_invalid_git_repo_scenario():
    """실제 시나리오: 잘못된 Git 저장소 처리"""
    print("\n" + "=" * 60)
    print("잘못된 Git 저장소 시나리오 테스트")
    print("=" * 60)

    # 싱글톤 리셋
    RepoCloneCache.reset_instance()
    cache = RepoCloneCache()

    # 잘못된 Git 저장소 디렉토리 생성
    fake_repo_dir = os.path.join(cache._cache_dir, "fake_repo_" + os.urandom(4).hex())

    print(f"\n1. 가짜 Git 저장소 생성: {fake_repo_dir}")
    os.makedirs(fake_repo_dir, exist_ok=True)

    # .git 폴더는 있지만 유효하지 않은 경우 시뮬레이션
    git_dir = os.path.join(fake_repo_dir, ".git")
    os.makedirs(git_dir, exist_ok=True)

    # 더미 파일 추가
    with open(os.path.join(git_dir, "config"), 'w') as f:
        f.write("invalid config")

    assert os.path.exists(fake_repo_dir), "가짜 저장소가 생성되지 않았습니다"
    print("✓ 가짜 Git 저장소 생성 완료")

    # 2. 삭제 및 재생성 시뮬레이션
    print(f"\n2. 삭제 및 즉시 재생성 시뮬레이션...")

    # 삭제
    cache._force_remove_directory(fake_repo_dir)
    print("✓ 삭제 완료")

    # 삭제 확인 (여러 번 재시도)
    import time
    max_attempts = 5
    for attempt in range(max_attempts):
        if not os.path.exists(fake_repo_dir):
            print(f"✓ 삭제 확인 완료 ({attempt + 1}회)")
            break
        if attempt < max_attempts - 1:
            print(f"  - 대기 중... ({attempt + 1}/{max_attempts})")
            time.sleep(0.5)
    else:
        raise AssertionError(f"디렉토리가 삭제되지 않았습니다: {fake_repo_dir}")

    # 즉시 재생성
    print(f"\n3. 동일한 경로에 재생성...")
    try:
        os.makedirs(fake_repo_dir, exist_ok=False)
        print("✓ 재생성 성공")
    except Exception as e:
        print(f"✗ 재생성 실패: {e}")
        raise
    finally:
        # 정리
        if os.path.exists(fake_repo_dir):
            shutil.rmtree(fake_repo_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print("시나리오 테스트 통과! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_directory_removal_and_recreation()
    test_invalid_git_repo_scenario()

    print("\n" + "=" * 60)
    print("전체 통합 테스트 완료! ✓✓✓")
    print("=" * 60)

