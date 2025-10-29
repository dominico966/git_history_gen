"""
tools.py 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.tools import (
    get_commit_summary,
    analyze_contributors,
    find_frequent_bug_commits
)


def test_analyze_contributors_no_commits():
    """커밋이 없는 경우 테스트"""
    with patch('src.tools.DocumentGenerator') as mock_gen:
        mock_instance = Mock()
        mock_instance.get_commits.return_value = []
        mock_gen.return_value = mock_instance

        result = analyze_contributors("fake_repo")
        assert "error" in result


def test_analyze_contributors_success():
    """정상적인 기여자 분석 테스트"""
    with patch('src.tools.DocumentGenerator') as mock_gen:
        mock_instance = Mock()
        mock_instance.get_commits.return_value = [
            {
                "id": "abc123",
                "message": "Test commit",
                "author": "John Doe",
                "date": "2025-01-01T00:00:00",
                "files": [
                    {"file": "test.py", "change_type": "M", "lines_added": 10, "lines_deleted": 5}
                ]
            },
            {
                "id": "def456",
                "message": "Another commit",
                "author": "John Doe",
                "date": "2025-01-02T00:00:00",
                "files": [
                    {"file": "test2.py", "change_type": "A", "lines_added": 20, "lines_deleted": 0}
                ]
            }
        ]
        mock_gen.return_value = mock_instance

        result = analyze_contributors("fake_repo", limit=10)

        assert result["total_contributors"] == 1
        assert result["total_commits"] == 2
        assert len(result["contributors"]) == 1

        contrib = result["contributors"][0]
        assert contrib["name"] == "John Doe"
        assert contrib["commits"] == 2
        assert contrib["lines_added"] == 30
        assert contrib["lines_deleted"] == 5


def test_find_frequent_bug_commits():
    """버그 커밋 찾기 테스트"""
    with patch('src.tools.DocumentGenerator') as mock_gen:
        mock_instance = Mock()
        mock_instance.get_commits.return_value = [
            {
                "id": "abc123",
                "message": "Fix bug in login",
                "author": "Jane Doe",
                "date": "2025-01-01T00:00:00",
                "files": [{"file": "login.py"}]
            },
            {
                "id": "def456",
                "message": "Add new feature",
                "author": "John Doe",
                "date": "2025-01-02T00:00:00",
                "files": [{"file": "feature.py"}]
            },
            {
                "id": "ghi789",
                "message": "Hotfix for critical issue",
                "author": "Jane Doe",
                "date": "2025-01-03T00:00:00",
                "files": [{"file": "critical.py"}]
            }
        ]
        mock_gen.return_value = mock_instance

        mock_llm = Mock()
        result = find_frequent_bug_commits("fake_repo", mock_llm, limit=100)

        # Should find 2 bug-related commits (containing 'fix', 'issue')
        assert len(result) == 2
        assert any("Fix bug" in r["message"] for r in result)
        assert any("Hotfix" in r["message"] for r in result)


def test_get_commit_summary_error_handling():
    """커밋 요약 에러 처리 테스트"""
    with patch('src.tools.DocumentGenerator') as mock_gen:
        mock_instance = Mock()
        mock_instance.get_commits.side_effect = Exception("Git error")
        mock_gen.return_value = mock_instance

        mock_llm = Mock()
        result = get_commit_summary("fake_repo", mock_llm)

        assert "Error" in result or "error" in result.lower()

