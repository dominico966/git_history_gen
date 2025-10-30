"""
get_commit_count 0개 커밋 응답 개선 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools import get_commit_count


def test_zero_commits_message():
    """커밋이 없는 기간에 대한 명확한 메시지 테스트"""
    repo_url = "https://github.com/Chainlit/chainlit"

    print("\n=== 테스트 1: 2022년 커밋 확인 (없을 것으로 예상) ===")
    result = get_commit_count(
        repo_path=repo_url,
        since="2022-01-01",
        until="2022-12-31"
    )

    print(f"결과:")
    print(f"  - commit_count: {result.get('commit_count', 0)}")
    print(f"  - has_commits: {result.get('has_commits', False)}")
    print(f"  - message: {result.get('message', '')}")

    # 검증
    assert 'commit_count' in result
    assert 'has_commits' in result
    assert 'message' in result

    if result['commit_count'] == 0:
        assert result['has_commits'] == False
        assert "커밋이 없습니다" in result['message'] or "저장소 개설일" in result['message']
        print("✅ 0개 커밋일 때 명확한 메시지 확인됨")
    else:
        print(f"⚠️ 예상과 다르게 {result['commit_count']}개 커밋 발견됨")


def test_has_commits_message():
    """커밋이 있는 기간에 대한 메시지 테스트"""
    repo_url = "https://github.com/Chainlit/chainlit"

    print("\n=== 테스트 2: 2024년 커밋 확인 (있을 것으로 예상) ===")
    result = get_commit_count(
        repo_path=repo_url,
        since="2024-01-01",
        until="2024-12-31"
    )

    print(f"결과:")
    print(f"  - commit_count: {result.get('commit_count', 0)}")
    print(f"  - has_commits: {result.get('has_commits', False)}")
    print(f"  - message: {result.get('message', '')}")

    # 검증
    assert 'commit_count' in result
    assert 'has_commits' in result
    assert 'message' in result

    if result['commit_count'] > 0:
        assert result['has_commits'] == True
        assert "총" in result['message']
        assert "커밋" in result['message']
        print(f"✅ {result['commit_count']}개 커밋 확인됨")
    else:
        print("⚠️ 예상과 다르게 커밋이 없음")


def test_no_date_range():
    """날짜 범위 없이 전체 커밋 확인"""
    repo_url = "https://github.com/Chainlit/chainlit"

    print("\n=== 테스트 3: 전체 커밋 확인 ===")
    result = get_commit_count(repo_path=repo_url)

    print(f"결과:")
    print(f"  - commit_count: {result.get('commit_count', 0)}")
    print(f"  - has_commits: {result.get('has_commits', False)}")
    print(f"  - message: {result.get('message', '')}")

    assert result['commit_count'] > 0, "전체 커밋은 반드시 있어야 함"
    assert result['has_commits'] == True
    print(f"✅ 전체 {result['commit_count']}개 커밋 확인됨")


if __name__ == "__main__":
    print("=" * 60)
    print("get_commit_count 0개 커밋 응답 테스트")
    print("=" * 60)

    try:
        test_zero_commits_message()
        test_has_commits_message()
        test_no_date_range()

        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

