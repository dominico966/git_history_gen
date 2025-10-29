"""
강화된 디렉토리 삭제 로직 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from src.repo_cache import RepoCloneCache
from src.document_generator import DocumentGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_force_removal():
    """강화된 삭제 로직 테스트"""
    logger.info("=" * 60)
    logger.info("강화된 디렉토리 삭제 로직 테스트")
    logger.info("=" * 60)

    test_url = "https://github.com/toeverything/AFFiNE"

    try:
        # 1단계: 캐시 초기화
        cache = RepoCloneCache()
        logger.info("캐시 정리 시작...")
        cache.clear_all()
        logger.info("✓ 캐시 정리 완료")

        # 2단계: 작은 저장소로 테스트
        test_small_url = "https://github.com/octocat/Hello-World"
        logger.info(f"\n작은 저장소 테스트: {test_small_url}")

        doc_gen = DocumentGenerator(test_small_url)
        try:
            commits = doc_gen.get_commits(limit=3)
            logger.info(f"✓ {len(commits)}개 커밋 추출")
        finally:
            doc_gen.close()

        # 3단계: 캐시 정리 재테스트
        logger.info("\n캐시 재정리 테스트...")
        cache.clear_all()
        logger.info("✓ 캐시 재정리 성공")

        logger.info("\n✓ 모든 테스트 통과!")
        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def main():
    """테스트 실행"""
    logger.info("\n" + "=" * 60)
    logger.info("디렉토리 삭제 강화 테스트")
    logger.info("=" * 60)

    success = test_force_removal()

    logger.info("\n" + "=" * 60)
    logger.info(f"결과: {'✓ 성공' if success else '✗ 실패'}")
    logger.info("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

