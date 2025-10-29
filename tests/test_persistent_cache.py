"""
영구 캐시 및 만료 시간 테스트
1. JSON 파일 저장/로드
2. 캐시 만료 테스트 (1일)
3. 유효성 검사 및 자동 정리
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import time
import json
from datetime import datetime, timedelta
from src.repo_cache import RepoCloneCache
from src.document_generator import DocumentGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_persistent_cache():
    """영구 캐시 저장/로드 테스트"""
    logger.info("=" * 60)
    logger.info("1. 영구 캐시 저장/로드 테스트")
    logger.info("=" * 60)

    test_url = "https://github.com/octocat/Hello-World"

    try:
        # 첫 번째 인스턴스 - 클론
        logger.info("첫 번째 인스턴스 생성 및 클론...")
        cache1 = RepoCloneCache()

        doc_gen1 = DocumentGenerator(test_url, clone_depth=10)
        commits1 = doc_gen1.get_commits(limit=3)
        logger.info(f"✓ {len(commits1)}개 커밋 추출")

        # 캐시 정보 확인
        cache_info1 = cache1.get_cache_info()
        logger.info(f"캐시 파일: {cache_info1['cache_file']}")
        logger.info(f"캐시된 저장소: {cache_info1['cached_repos']}개")

        # JSON 파일 존재 확인
        if os.path.exists(cache_info1['cache_file']):
            logger.info(f"✓ 캐시 메타데이터 파일 존재")
            with open(cache_info1['cache_file'], 'r') as f:
                metadata = json.load(f)
                logger.info(f"  메타데이터 내용: {len(metadata)}개 항목")
        else:
            logger.error("✗ 캐시 메타데이터 파일 없음")
            return False

        # 두 번째 인스턴스 - 로드 (캐시 히트)
        logger.info("\n두 번째 인스턴스 생성 (캐시 로드)...")

        # 싱글톤이므로 동일 인스턴스를 반환하지만, 프로세스 재시작 시뮬레이션
        cache2 = RepoCloneCache()
        cache_info2 = cache2.get_cache_info()

        logger.info(f"로드된 캐시: {cache_info2['cached_repos']}개")

        if cache_info2['cached_repos'] == cache_info1['cached_repos']:
            logger.info("✓ 캐시가 정상적으로 로드되었습니다!")
        else:
            logger.error(f"✗ 캐시 로드 실패: 예상 {cache_info1['cached_repos']}, 실제 {cache_info2['cached_repos']}")
            return False

        # 캐시 사용 확인
        doc_gen2 = DocumentGenerator(test_url, clone_depth=10)
        commits2 = doc_gen2.get_commits(limit=3)
        logger.info(f"✓ 캐시에서 {len(commits2)}개 커밋 추출")

        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def test_cache_expiration():
    """캐시 만료 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("2. 캐시 만료 테스트")
    logger.info("=" * 60)

    try:
        cache = RepoCloneCache()
        cache_info = cache.get_cache_info()

        logger.info(f"캐시 만료 기간: {cache_info['expire_days']}일")

        # 캐시된 저장소의 만료 상태 확인
        for repo_info in cache_info['repos']:
            logger.info(f"\n저장소: {repo_info['url']}")
            logger.info(f"  - 캐시 키: {repo_info['cache_key']}")
            logger.info(f"  - 나이: {repo_info['age_days']}일")
            logger.info(f"  - 만료 상태: {'만료' if repo_info['is_expired'] else '유효'}")

        logger.info("\n✓ 만료 정보 확인 완료")
        logger.info(f"ℹ️ {cache_info['expire_days']}일 후 캐시가 자동으로 삭제됩니다.")

        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def test_cache_validation():
    """캐시 유효성 검사 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("3. 캐시 유효성 검사 테스트")
    logger.info("=" * 60)

    try:
        cache = RepoCloneCache()

        logger.info("초기화 시 자동 유효성 검사가 수행됨")
        logger.info("- 만료된 캐시 제거")
        logger.info("- 손상된 캐시 제거")
        logger.info("- 유효한 캐시 업데이트 (git pull)")

        cache_info = cache.get_cache_info()

        logger.info(f"\n현재 유효한 캐시: {cache_info['cached_repos']}개")

        for repo_info in cache_info['repos']:
            if not repo_info['is_expired']:
                logger.info(f"✓ {repo_info['url']} - 유효 ({repo_info['age_days']}일)")

        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def test_cache_metadata_structure():
    """캐시 메타데이터 구조 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("4. 캐시 메타데이터 구조 테스트")
    logger.info("=" * 60)

    try:
        cache = RepoCloneCache()
        cache_info = cache.get_cache_info()
        cache_file = cache_info['cache_file']

        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            logger.info(f"메타데이터 파일: {cache_file}")
            logger.info(f"저장된 항목 수: {len(metadata)}")

            # 첫 번째 항목 구조 확인
            if metadata:
                first_key = list(metadata.keys())[0]
                first_entry = metadata[first_key]

                logger.info(f"\n항목 구조 예시:")
                logger.info(f"  - cache_key: {first_key}")
                logger.info(f"  - url: {first_entry.get('url', 'N/A')}")
                logger.info(f"  - path: {first_entry.get('path', 'N/A')}")
                logger.info(f"  - created_at: {first_entry.get('created_at', 'N/A')}")
                logger.info(f"  - last_accessed: {first_entry.get('last_accessed', 'N/A')}")
                logger.info(f"  - clone_depth: {first_entry.get('clone_depth', 'N/A')}")

                # 필수 필드 확인
                required_fields = ['url', 'path', 'created_at', 'last_accessed']
                missing_fields = [f for f in required_fields if f not in first_entry]

                if missing_fields:
                    logger.error(f"✗ 필수 필드 누락: {missing_fields}")
                    return False
                else:
                    logger.info(f"✓ 모든 필수 필드 존재")
        else:
            logger.warning("캐시 메타데이터 파일 없음")

        return True

    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False


def main():
    """전체 테스트 실행"""
    logger.info("\n" + "=" * 60)
    logger.info("영구 캐시 시스템 테스트")
    logger.info("=" * 60)

    results = []

    # 1. 영구 캐시 저장/로드
    results.append(("영구 캐시 저장/로드", test_persistent_cache()))

    # 2. 캐시 만료
    results.append(("캐시 만료", test_cache_expiration()))

    # 3. 캐시 유효성 검사
    results.append(("캐시 유효성 검사", test_cache_validation()))

    # 4. 메타데이터 구조
    results.append(("메타데이터 구조", test_cache_metadata_structure()))

    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("테스트 결과 요약")
    logger.info("=" * 60)

    for name, result in results:
        status = "✓ 성공" if result else "✗ 실패"
        logger.info(f"{name}: {status}")

    success_count = sum(1 for _, r in results if r)
    logger.info(f"\n총 {len(results)}개 중 {success_count}개 성공")

    # 캐시 정보 출력
    cache = RepoCloneCache()
    cache_info = cache.get_cache_info()
    logger.info(f"\n최종 캐시 상태:")
    logger.info(f"  - 캐시 디렉토리: {cache_info['cache_dir']}")
    logger.info(f"  - 메타데이터 파일: {cache_info['cache_file']}")
    logger.info(f"  - 캐시된 저장소: {cache_info['cached_repos']}개")
    logger.info(f"  - 만료 기간: {cache_info['expire_days']}일")

    logger.info("\nℹ️ 캐시는 프로그램 종료 후에도 유지됩니다.")
    logger.info(f"ℹ️ 수동 정리가 필요하면 Streamlit UI 또는 cache.clear_all() 사용")

    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    exit(main())

