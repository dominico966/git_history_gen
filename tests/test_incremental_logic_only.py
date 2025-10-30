"""
증분 인덱싱 로직 검증 - 단순 로직 테스트
"""
import pytest


def test_incremental_logic_calculation():
    """증분 인덱싱 계산 로직 검증"""

    # 시나리오 1: 1124개 요청, 200개 이미 있음
    original_limit = 1124
    existing_count = 200

    if original_limit > existing_count:
        adjusted_limit = original_limit - existing_count
        skip_offset = existing_count

        assert adjusted_limit == 924, f"Expected 924, got {adjusted_limit}"
        assert skip_offset == 200, f"Expected 200, got {skip_offset}"

    # 시나리오 2: 200개 요청, 200개 이미 있음 (조기 종료)
    original_limit = 200
    existing_count = 200

    should_index = original_limit > existing_count
    assert not should_index, "Should not index when enough commits exist"

    # 시나리오 3: 3000개 요청, 100개 이미 있음, cap=2000
    original_limit = 3000
    existing_count = 100
    MAX_COMMIT_LIMIT = 2000

    if original_limit > existing_count:
        adjusted_limit = original_limit - existing_count  # 2900
        skip_offset = existing_count  # 100

        # cap 적용
        if adjusted_limit > MAX_COMMIT_LIMIT:
            adjusted_limit = MAX_COMMIT_LIMIT

        assert adjusted_limit == 2000, f"Expected 2000 (capped), got {adjusted_limit}"
        assert skip_offset == 100, f"Expected 100, got {skip_offset}"


def test_cap_order_matters():
    """cap이 증분 인덱싱 계산 전에 적용되면 잘못된 결과"""

    # ❌ 잘못된 순서: cap → 증분 계산
    original_limit = 1124
    MAX_COMMIT_LIMIT = 200

    # cap 먼저 적용 (잘못됨)
    if original_limit > MAX_COMMIT_LIMIT:
        capped_limit = MAX_COMMIT_LIMIT  # 200
    else:
        capped_limit = original_limit

    # 증분 계산
    existing_count = 200
    if capped_limit <= existing_count:
        should_index = False
    else:
        should_index = True
        adjusted = capped_limit - existing_count

    # 결과: 인덱싱 안 함 (잘못됨!)
    assert not should_index, "Wrong: capping before incremental calculation prevents indexing"

    # ✅ 올바른 순서: 증분 계산 → cap
    original_limit = 1124
    existing_count = 200

    # 증분 계산 먼저
    if original_limit > existing_count:
        adjusted_limit = original_limit - existing_count  # 924
        skip_offset = existing_count  # 200

        # cap 적용
        if adjusted_limit > MAX_COMMIT_LIMIT:
            adjusted_limit = MAX_COMMIT_LIMIT  # 200

        should_index = True
    else:
        should_index = False

    # 결과: 인덱싱 진행 (200개만, 하지만 skip_offset=200이므로 201~400번째 커밋)
    assert should_index, "Correct: incremental calculation before cap allows indexing"
    assert adjusted_limit == 200, f"Expected 200 (capped), got {adjusted_limit}"
    assert skip_offset == 200, f"Expected skip_offset=200, got {skip_offset}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

