"""
캐싱 및 컨텍스트 개선 테스트
1. 원격 저장소 클론 캐싱 테스트
2. 변경 컨텍스트 추출 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import time
from src.document_generator import DocumentGenerator
from src.repo_cache import RepoCloneCache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_clone_caching():
    """원격 저장소 클론 캐싱 테스트"""
    logger.info("=" * 60)
    logger.info("1. 원격 저장소 클론 캐싱 테스트")
    logger.info("=" * 60)

    test_url = "https://github.com/octocat/Hello-World"

    try:
        # 첫 번째 클론 (캐시 미스)
        logger.info("첫 번째 클론 (캐시 미스 예상)...")
        start_time = time.time()

        doc_gen1 = DocumentGenerator(test_url, clone_depth=10)
        commits1 = doc_gen1.get_commits(limit=5)

        first_clone_time = time.time() - start_time
        logger.info(f"✓ 첫 번째 클론 완료: {first_clone_time:.2f}초, {len(commits1)}개 커밋")

        # 두 번째 클론 (캐시 히트)
        logger.info("\n두 번째 클론 (캐시 히트 예상)...")
        start_time = time.time()

        doc_gen2 = DocumentGenerator(test_url, clone_depth=10)
        commits2 = doc_gen2.get_commits(limit=5)

        second_clone_time = time.time() - start_time
        logger.info(f"✓ 두 번째 클론 완료: {second_clone_time:.2f}초, {len(commits2)}개 커밋")

        # 성능 비교
        speedup = first_clone_time / second_clone_time if second_clone_time > 0 else 0
        logger.info(f"\n성능 개선: {speedup:.1f}배 빠름 (캐시 효과)")

        if speedup > 2:
            logger.info("✓ 캐싱이 정상적으로 작동하고 있습니다!")
        else:
            logger.warning("⚠️ 캐싱 효과가 예상보다 작습니다.")

        # 캐시 정보 확인
        cache = RepoCloneCache()
        cache_info = cache.get_cache_info()
        logger.info(f"\n캐시 정보: {cache_info['cached_repos']}개 저장소 캐시됨")

        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def test_change_context():
    """변경 컨텍스트 추출 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("2. 변경 컨텍스트 추출 테스트")
    logger.info("=" * 60)

    test_url = "https://github.com/octocat/Hello-World"

    try:
        doc_gen = DocumentGenerator(test_url, clone_depth=10)
        commits = doc_gen.get_commits(limit=3)

        logger.info(f"✓ {len(commits)}개 커밋 추출")

        # 각 커밋의 변경 컨텍스트 확인
        for i, commit in enumerate(commits, 1):
            logger.info(f"\n--- 커밋 {i} ---")
            logger.info(f"SHA: {commit['id'][:8]}")
            logger.info(f"Message: {commit['message'][:50]}")
            logger.info(f"Files: {len(commit['files'])}")

            # 파일별 컨텍스트 확인
            for file_info in commit['files']:
                file_path = file_info['file']
                logger.info(f"\n  📄 {file_path}")
                logger.info(f"     +{file_info['lines_added']} -{file_info['lines_deleted']}")

                # 변경 컨텍스트가 있는지 확인
                if 'change_context' in file_info:
                    contexts = file_info['change_context']
                    logger.info(f"     ✓ {len(contexts)}개 변경 블록의 컨텍스트 추출됨")

                    for j, ctx in enumerate(contexts[:1], 1):  # 첫 번째 블록만 표시
                        snippet = ctx['snippet'][:200]  # 처음 200자만
                        logger.info(f"     블록 {j} (라인 {ctx['start_line']}~):")
                        logger.info(f"     {snippet[:100]}...")
                else:
                    logger.info(f"     ℹ️ 변경 컨텍스트 없음 (바이너리 파일 또는 추출 실패)")

        logger.info("\n✓ 변경 컨텍스트 추출 테스트 완료")
        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def test_multiple_repos():
    """여러 저장소 캐싱 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("3. 여러 저장소 캐싱 테스트")
    logger.info("=" * 60)

    repos = [
        "https://github.com/octocat/Hello-World",
        "https://github.com/octocat/Spoon-Knife"
    ]

    try:
        cache = RepoCloneCache()

        for repo_url in repos:
            logger.info(f"\n처리 중: {repo_url}")
            doc_gen = DocumentGenerator(repo_url, clone_depth=5)
            commits = doc_gen.get_commits(limit=3)
            logger.info(f"✓ {len(commits)}개 커밋 추출")

        # 최종 캐시 상태
        cache_info = cache.get_cache_info()
        logger.info(f"\n최종 캐시 상태:")
        logger.info(f"  - 캐시된 저장소: {cache_info['cached_repos']}개")
        logger.info(f"  - 캐시 디렉토리: {cache_info['cache_dir']}")

        if cache_info['cached_repos'] == len(repos):
            logger.info("✓ 모든 저장소가 캐시되었습니다!")
        else:
            logger.warning(f"⚠️ 예상: {len(repos)}개, 실제: {cache_info['cached_repos']}개")

        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def main():
    """전체 테스트 실행"""
    logger.info("\n" + "=" * 60)
    logger.info("캐싱 및 컨텍스트 개선 테스트 시작")
    logger.info("=" * 60)

    results = []

    # 1. 클론 캐싱 테스트
    results.append(("클론 캐싱", test_clone_caching()))

    # 2. 변경 컨텍스트 테스트
    results.append(("변경 컨텍스트", test_change_context()))

    # 3. 여러 저장소 캐싱 테스트
    results.append(("여러 저장소 캐싱", test_multiple_repos()))

    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("테스트 결과 요약")
    logger.info("=" * 60)

    for name, result in results:
        status = "✓ 성공" if result else "✗ 실패"
        logger.info(f"{name}: {status}")

    success_count = sum(1 for _, r in results if r)
    logger.info(f"\n총 {len(results)}개 중 {success_count}개 성공")

    # 캐시 정리
    logger.info("\n캐시 정리 중...")
    cache = RepoCloneCache()
    cache.clear_all()
    logger.info("✓ 캐시 정리 완료")

    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    exit(main())

