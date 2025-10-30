"""
analyze_contributors 함수의 날짜 범위 파라미터 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools import analyze_contributors


def test_analyze_contributors_with_date_range():
    """날짜 범위를 지정한 기여자 분석 테스트"""
    # 현재 프로젝트 저장소를 사용
    repo_path = str(project_root)

    # 날짜 범위를 지정하여 기여자 분석 (2025년 1월 이후)
    result = analyze_contributors(
        repo_path=repo_path,
        since="2025-01-01",
        limit=100
    )

    print("\n=== 날짜 범위 지정 기여자 분석 결과 ===")
    print(f"기간: 2025-01-01 이후")
    print(f"총 기여자: {result.get('total_contributors', 0)}명")
    print(f"총 커밋: {result.get('total_commits', 0)}개")

    if 'contributors' in result and result['contributors']:
        print("\n상위 5명 기여자:")
        for i, contributor in enumerate(result['contributors'][:5], 1):
            print(f"{i}. {contributor['name']}")
            print(f"   - 커밋: {contributor['commits']}개")
            print(f"   - 추가: {contributor['lines_added']}줄")
            print(f"   - 삭제: {contributor['lines_deleted']}줄")
            print(f"   - 총 변경: {contributor['total_lines_changed']}줄")

    assert 'total_contributors' in result
    assert 'total_commits' in result
    assert 'contributors' in result


def test_analyze_contributors_without_date_range():
    """날짜 범위 없이 기여자 분석 테스트 (기존 동작)"""
    repo_path = str(project_root)

    # 날짜 범위 없이 기여자 분석
    result = analyze_contributors(
        repo_path=repo_path,
        limit=100
    )

    print("\n\n=== 날짜 범위 미지정 기여자 분석 결과 ===")
    print(f"총 기여자: {result.get('total_contributors', 0)}명")
    print(f"총 커밋: {result.get('total_commits', 0)}개")

    if 'contributors' in result:
        print("\n상위 3명 기여자:")
        for i, contributor in enumerate(result['contributors'][:3], 1):
            print(f"{i}. {contributor['name']}: {contributor['commits']}개 커밋")

    assert 'total_contributors' in result
    assert 'total_commits' in result
    assert 'contributors' in result


def test_analyze_contributors_only_since():
    """since 파라미터만 사용한 테스트"""
    repo_path = str(project_root)

    result = analyze_contributors(
        repo_path=repo_path,
        since="2025-10-01",
        limit=50
    )

    print("\n\n=== since 파라미터만 사용 ===")
    print(f"기간: 2025-10-01 이후")
    print(f"총 기여자: {result.get('total_contributors', 0)}명")
    print(f"총 커밋: {result.get('total_commits', 0)}개")

    assert 'total_contributors' in result


if __name__ == "__main__":
    test_analyze_contributors_with_date_range()
    test_analyze_contributors_without_date_range()
    test_analyze_contributors_only_since()
    print("\n✅ 모든 테스트 통과!")

