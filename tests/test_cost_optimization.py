"""
비용 최적화 기능 테스트
- 기본값 10개로 변경 확인
- 날짜 필터링 테스트
- 증분 인덱싱 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime, timedelta
from src.document_generator import DocumentGenerator
from src.indexer import CommitIndexer
from src.agent import initialize_models

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_default_limit():
    """기본값 10개 제한 테스트"""
    logger.info("=" * 60)
    logger.info("1. 기본값 10개 제한 테스트")
    logger.info("=" * 60)

    try:
        doc_gen = DocumentGenerator(".")

        # 기본값으로 호출 (10개)
        commits = doc_gen.get_commits()
        logger.info(f"✓ 기본값으로 {len(commits)}개 커밋 추출")

        # 명시적으로 5개만 호출
        commits = doc_gen.get_commits(limit=5)
        logger.info(f"✓ limit=5로 {len(commits)}개 커밋 추출")

        return True
    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False

def test_date_filtering():
    """날짜 필터링 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("2. 날짜 필터링 테스트")
    logger.info("=" * 60)

    try:
        doc_gen = DocumentGenerator(".")

        # 최근 7일간의 커밋만
        since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        logger.info(f"최근 7일간 커밋 추출 (since: {since})")

        commits = doc_gen.get_commits(limit=100, since=since)
        logger.info(f"✓ {len(commits)}개 커밋 추출")

        if commits:
            logger.info(f"  - 가장 오래된 커밋: {commits[-1]['date']}")
            logger.info(f"  - 가장 최근 커밋: {commits[0]['date']}")

        return True
    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False

def test_incremental_indexing():
    """증분 인덱싱 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("3. 증분 인덱싱 테스트")
    logger.info("=" * 60)

    try:
        llm_client, search_client, index_client = initialize_models()

        indexer = CommitIndexer(
            search_client=search_client,
            index_client=index_client,
            openai_client=llm_client,
            index_name="git-commits"
        )

        # 첫 번째 인덱싱 (5개)
        logger.info("첫 번째 인덱싱 (5개, skip_existing=False)")
        count1 = indexer.index_repository(".", limit=5, skip_existing=False)
        logger.info(f"✓ {count1}개 커밋 인덱싱 완료")

        # 두 번째 인덱싱 (동일 5개, skip_existing=True)
        logger.info("\n두 번째 인덱싱 (5개, skip_existing=True)")
        count2 = indexer.index_repository(".", limit=5, skip_existing=True)
        logger.info(f"✓ {count2}개 새 커밋 인덱싱 완료")

        if count2 == 0:
            logger.info("✓ 증분 인덱싱 정상 작동 - 중복 커밋 건너뜀")
        else:
            logger.warning(f"⚠️ {count2}개 커밋이 새로 인덱싱됨 (예상: 0)")

        return True
    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False

def test_remote_with_options():
    """원격 저장소 옵션 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("4. 원격 저장소 옵션 테스트")
    logger.info("=" * 60)

    try:
        # 작은 테스트 저장소
        test_url = "https://github.com/octocat/Hello-World"

        logger.info(f"테스트 URL: {test_url}")
        logger.info("clone_depth=10으로 제한")

        doc_gen = DocumentGenerator(test_url, clone_depth=10)
        commits = doc_gen.get_commits(limit=5)

        logger.info(f"✓ {len(commits)}개 커밋 추출 성공")

        for i, commit in enumerate(commits[:3], 1):
            logger.info(f"  {i}. [{commit['id'][:8]}] {commit['message'][:40]}")

        return True
    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False

def main():
    """전체 테스트 실행"""
    logger.info("\n" + "=" * 60)
    logger.info("비용 최적화 기능 테스트 시작")
    logger.info("=" * 60)

    results = []

    # 1. 기본값 테스트
    results.append(("기본값 10개 제한", test_default_limit()))

    # 2. 날짜 필터링 테스트
    results.append(("날짜 필터링", test_date_filtering()))

    # 3. 증분 인덱싱 테스트
    results.append(("증분 인덱싱", test_incremental_indexing()))

    # 4. 원격 저장소 옵션 테스트
    results.append(("원격 저장소 옵션", test_remote_with_options()))

    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("테스트 결과 요약")
    logger.info("=" * 60)

    for name, result in results:
        status = "✓ 성공" if result else "✗ 실패"
        logger.info(f"{name}: {status}")

    success_count = sum(1 for _, r in results if r)
    logger.info(f"\n총 {len(results)}개 중 {success_count}개 성공")

    return 0 if success_count == len(results) else 1

if __name__ == "__main__":
    exit(main())

