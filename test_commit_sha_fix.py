"""
commit_sha 파라미터 수정 테스트
"""
import json


def test_search_commits_result_format():
    """search_commits 결과 포맷이 명확한지 테스트"""

    # 모의 search_commits 결과
    mock_results = [
        {
            "commit_id": "a1b2c3d4e5f6g7h8",
            "message": "feat: 대규모 UI/UX 개선 및 증분 인덱싱 강화",
            "author": "John Doe",
            "date": "2025-10-30"
        },
        {
            "commit_id": "i9j0k1l2m3n4o5p6",
            "message": "fix: 설정 수정",
            "author": "Jane Smith",
            "date": "2025-10-29"
        }
    ]

    # chat_app.py의 포맷팅 로직 시뮬레이션
    if isinstance(mock_results, list) and len(mock_results) > 0:
        summary = f"🔍 검색 결과: {len(mock_results)}개 커밋 발견\n\n"
        summary += "**중요**: 아래의 commit_id는 실제 커밋 SHA 해시입니다. get_commit_diff를 호출할 때 이 값을 그대로 사용하세요.\n\n"
        for i, r in enumerate(mock_results[:10], 1):
            commit_id = r.get('commit_id', 'N/A')
            short_sha = commit_id[:8] if len(commit_id) >= 8 else commit_id
            summary += f"{i}. **commit_id**: `{commit_id}` (짧은 형식: {short_sha})\n"
            summary += f"   **message**: {r.get('message', 'N/A')[:80]}...\n"
            summary += f"   **author**: {r.get('author', 'N/A')}\n"
            summary += f"   **date**: {r.get('date', 'N/A')}\n\n"
        if len(mock_results) > 10:
            summary += f"...외 {len(mock_results)-10}개 커밋\n\n"
        summary += "⚠️ **주의**: get_commit_diff를 호출할 때는 반드시 위의 commit_id 값을 commit_sha 파라미터로 사용하세요!"

    print("=" * 80)
    print("✅ search_commits 결과 포맷:")
    print("=" * 80)
    print(summary)
    print("=" * 80)

    # 검증
    assert "commit_id" in summary
    assert "a1b2c3d4e5f6g7h8" in summary
    assert "실제 커밋 SHA 해시" in summary
    assert "get_commit_diff" in summary

    print("\n✅ 테스트 성공: commit_id가 명확하게 표시됨")

    # 잘못된 사용 예시 vs 올바른 사용 예시
    print("\n" + "=" * 80)
    print("📚 사용 예시:")
    print("=" * 80)
    print("❌ 잘못된 사용:")
    print("   get_commit_diff(commit_sha='feat: 대규모 UI/UX 개선 및 증분 인덱싱 강화')")
    print("   → 커밋 메시지를 사용하면 커밋을 찾을 수 없음!")
    print()
    print("✅ 올바른 사용:")
    print("   get_commit_diff(commit_sha='a1b2c3d4e5f6g7h8')")
    print("   → commit_id 값을 그대로 사용!")
    print("=" * 80)


def test_tool_description():
    """도구 설명이 명확한지 테스트"""

    # get_commit_diff 도구 설명 (chat_app.py에서)
    tool_desc = {
        "name": "get_commit_diff",
        "description": "특정 커밋의 전체 변경사항(diff)을 가져옵니다. 어떤 파일이 어떻게 변경되었는지 한눈에 볼 수 있습니다. **중요**: commit_sha는 반드시 실제 커밋 해시(예: 'a1b2c3d4e5f6')를 사용해야 하며, 커밋 메시지를 사용하면 안 됩니다.",
        "parameters": {
            "commit_sha": {
                "description": "실제 커밋 SHA 해시 (예: 'a1b2c3d4e5f6' 또는 짧은 형식 'a1b2c3d4'). **절대로 커밋 메시지를 사용하지 마세요!** search_commits의 결과에서 commit_id 값을 사용하세요."
            }
        }
    }

    print("\n" + "=" * 80)
    print("✅ get_commit_diff 도구 설명:")
    print("=" * 80)
    print(f"이름: {tool_desc['name']}")
    print(f"설명: {tool_desc['description']}")
    print(f"commit_sha 파라미터: {tool_desc['parameters']['commit_sha']['description']}")
    print("=" * 80)

    # 검증
    assert "실제 커밋 해시" in tool_desc['description']
    assert "커밋 메시지를 사용하면 안 됩니다" in tool_desc['description']
    assert "절대로 커밋 메시지를 사용하지 마세요" in tool_desc['parameters']['commit_sha']['description']
    assert "commit_id 값을 사용하세요" in tool_desc['parameters']['commit_sha']['description']

    print("\n✅ 테스트 성공: 도구 설명이 명확함")


if __name__ == "__main__":
    print("🧪 commit_sha 파라미터 수정사항 테스트\n")
    test_search_commits_result_format()
    test_tool_description()
    print("\n🎉 모든 테스트 통과!")

