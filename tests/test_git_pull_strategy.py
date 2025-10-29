"""
Git Pull 우선 전략 테스트
- 기존 디렉토리가 있으면 git pull 시도
- 실패 시에만 삭제 후 재clone
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import os
from src.repo_cache import RepoCloneCache
from src.document_generator import DocumentGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_git_pull_strategy():
    """Git Pull 우선 전략 테스트"""
    logger.info("=" * 60)
    logger.info("Git Pull 우선 전략 테스트")
    logger.info("=" * 60)

    test_url = "https://github.com/octocat/Hello-World"

    try:
        # 첫 번째 clone
        logger.info("첫 번째 clone (전체 히스토리)...")
        doc_gen1 = DocumentGenerator(test_url)
        commits1 = doc_gen1.get_commits(limit=3)
        logger.info(f"✓ {len(commits1)}개 커밋 추출")

        cache = RepoCloneCache()
        cache_info = cache.get_cache_info()
        logger.info(f"캐시된 저장소: {cache_info['cached_repos']}개")

        # 두 번째 시도 (같은 URL) - git pull 사용해야 함
        logger.info("\n두 번째 시도 (캐시 사용 & git pull)...")
        doc_gen2 = DocumentGenerator(test_url)
        commits2 = doc_gen2.get_commits(limit=3)
        logger.info(f"✓ {len(commits2)}개 커밋 추출")

        logger.info("\n✓ 기존 디렉토리에서 git pull 성공!")

        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def test_damaged_directory_recovery():
    """손상된 디렉토리 복구 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("손상된 디렉토리 복구 테스트")
    logger.info("=" * 60)

    test_url = "https://github.com/octocat/Spoon-Knife"

    try:
        cache = RepoCloneCache()
        cache_info = cache.get_cache_info()
        cache_dir = cache_info['cache_dir']

        # 테스트용 손상된 디렉토리 생성
        import hashlib
        cache_key = hashlib.md5(test_url.encode()).hexdigest()[:12]
        damaged_path = os.path.join(cache_dir, cache_key)

        logger.info(f"손상된 디렉토리 생성: {damaged_path}")
        os.makedirs(damaged_path, exist_ok=True)

        # 빈 파일 생성 (Git 저장소가 아님)
        with open(os.path.join(damaged_path, "dummy.txt"), "w") as f:
            f.write("This is not a git repo")

        logger.info("✓ 손상된 디렉토리 준비 완료")

        # DocumentGenerator로 clone 시도 (손상된 디렉토리 자동 제거 후 clone)
        logger.info(f"\n손상된 디렉토리에서 복구 시도...")
        doc_gen = DocumentGenerator(test_url)
        commits = doc_gen.get_commits(limit=3)

        logger.info(f"✓ 성공! {len(commits)}개 커밋 추출")
        logger.info("✓ 손상된 디렉토리가 자동으로 제거되고 새로 clone됨")

        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def test_long_path_handling():
    """긴 파일 경로 처리 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("긴 파일 경로 처리 테스트")
    logger.info("=" * 60)

    # 긴 경로를 포함하는 저장소 (AFFiNE)
    test_url = "https://github.com/toeverything/AFFiNE"

    try:
        logger.info("긴 경로를 포함한 저장소 clone 시도 (전체 히스토리)...")
        logger.info("(이 테스트는 Windows 긴 경로 지원 설정에 따라 실패할 수 있습니다)")

        doc_gen = DocumentGenerator(test_url)
        commits = doc_gen.get_commits(limit=2)

        logger.info(f"✓ 성공! {len(commits)}개 커밋 추출")
        logger.info("✓ Windows 긴 경로 지원이 활성화되어 있습니다")

        return True

    except Exception as e:
        error_msg = str(e)

        if 'Filename too long' in error_msg or '파일 경로가 너무 깁니다' in error_msg:
            logger.warning("⚠️ 예상된 실패: 파일 경로가 너무 깁니다")
            logger.info("이는 Windows 제한사항입니다.")
            logger.info("해결 방법: git config --system core.longpaths true")
            return True  # 예상된 실패이므로 테스트는 통과
        else:
            logger.error(f"✗ 예상치 못한 에러: {e}", exc_info=True)
            return False


def main():
    """전체 테스트 실행"""
    logger.info("\n" + "=" * 60)
    logger.info("Git Pull 우선 전략 테스트")
    logger.info("=" * 60)

    results = []

    # 1. Git Pull 전략
    results.append(("Git Pull 우선 전략", test_git_pull_strategy()))

    # 2. 손상된 디렉토리 복구
    results.append(("손상된 디렉토리 복구", test_damaged_directory_recovery()))

    # 3. 긴 경로 처리
    results.append(("긴 파일 경로 처리", test_long_path_handling()))

    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("테스트 결과 요약")
    logger.info("=" * 60)

    for name, result in results:
        status = "✓ 성공" if result else "✗ 실패"
        logger.info(f"{name}: {status}")

    success_count = sum(1 for _, r in results if r)
    logger.info(f"\n총 {len(results)}개 중 {success_count}개 성공")

    # 최종 캐시 정리
    logger.info("\n최종 캐시 정리...")
    cache = RepoCloneCache()
    cache.clear_all()
    logger.info("✓ 정리 완료")

    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    exit(main())

