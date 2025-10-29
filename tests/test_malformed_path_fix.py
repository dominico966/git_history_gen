"""
잘못된 캐시 경로 패턴을 감지하고 수정하는 테스트
"""

import logging
import sys
import os
import json
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


def test_malformed_path_detection():
    """잘못된 경로 패턴을 감지하고 수정하는 테스트"""
    print("\n" + "=" * 60)
    print("잘못된 경로 패턴 감지 테스트")
    print("=" * 60)

    # 싱글톤 리셋
    RepoCloneCache.reset_instance()
    cache = RepoCloneCache()

    # 잘못된 경로 패턴 시뮬레이션
    malformed_path = "C:\\Users\\User\\IdeaProjects\\git_history_gen.cache\\repos\\4815469146dd"
    cache_key = "test_key_123"

    print(f"\n1. 잘못된 경로: {malformed_path}")
    print(f"   (주의: 'git_history_gen.cache' - 백슬래시 없이 점으로 붙어있음)")

    # _normalize_cache_path 호출
    normalized = cache._normalize_cache_path(malformed_path, cache_key)

    print(f"\n2. 정규화된 경로: {normalized}")

    # 검증
    assert 'git_history_gen\\.cache' in normalized or 'git_history_gen/.cache' in normalized, \
        f"정규화 실패: {normalized}"

    assert 'git_history_gen.cache' not in normalized.replace('\\', '/'), \
        f"여전히 잘못된 패턴이 포함됨: {normalized}"

    print("\n✓ 잘못된 경로가 성공적으로 수정되었습니다!")

    # 올바른 경로는 변경되지 않아야 함
    correct_path = cache._cache_dir + "\\test_key_456"
    normalized_correct = cache._normalize_cache_path(correct_path, "test_key_456")

    assert correct_path == normalized_correct, \
        f"올바른 경로가 잘못 변경됨: {correct_path} -> {normalized_correct}"

    print("✓ 올바른 경로는 변경되지 않았습니다!")

    # 경로 검증
    print(f"\n현재 캐시 디렉토리: {cache._cache_dir}")
    cache_path = Path(cache._cache_dir)
    print(f"Path parts: {cache_path.parts}")

    print("\n" + "=" * 60)
    print("모든 테스트 통과! ✓")
    print("=" * 60)


def test_cache_metadata_with_malformed_path():
    """잘못된 경로가 포함된 메타데이터 처리 테스트"""
    print("\n" + "=" * 60)
    print("잘못된 메타데이터 처리 테스트")
    print("=" * 60)

    # 싱글톤 리셋
    RepoCloneCache.reset_instance()
    cache = RepoCloneCache()

    # 캐시에 잘못된 경로 추가 (시뮬레이션)
    malformed_entry = {
        'url': 'https://github.com/test/repo.git',
        'path': 'C:\\Users\\User\\IdeaProjects\\git_history_gen.cache\\repos\\abc123def456',
        'created_at': '2025-01-28T10:00:00',
        'last_accessed': '2025-01-28T10:00:00'
    }

    cache._cache['abc123def456'] = malformed_entry

    print(f"\n잘못된 경로가 추가됨: {malformed_entry['path']}")

    # _validate_and_cleanup_cache 호출 (내부에서 정규화 수행)
    try:
        cache._validate_and_cleanup_cache()
        print("\n✓ 검증 및 정규화 완료")
    except Exception as e:
        print(f"\n⚠ 검증 중 에러 (예상됨): {e}")

    # 캐시 엔트리가 정규화되었는지 확인
    if 'abc123def456' in cache._cache:
        updated_path = cache._cache['abc123def456']['path']
        print(f"\n정규화된 경로: {updated_path}")

        # 검증
        assert '.cache' in updated_path, "경로에 .cache가 포함되어야 함"
        assert 'git_history_gen.cache' not in updated_path.replace('\\', '/'), \
            "잘못된 패턴이 여전히 존재"

        print("✓ 캐시 엔트리가 성공적으로 정규화되었습니다!")
    else:
        print("✓ 잘못된 캐시 엔트리가 제거되었습니다!")

    print("\n" + "=" * 60)
    print("메타데이터 처리 테스트 통과! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_malformed_path_detection()
    test_cache_metadata_with_malformed_path()

    print("\n" + "=" * 60)
    print("전체 테스트 완료! ✓✓✓")
    print("=" * 60)

