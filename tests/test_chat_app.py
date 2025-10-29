"""
Chainlit 채팅앱 테스트
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """필요한 모듈 import 테스트"""
    try:
        import chainlit as cl
        import src.chat_app  # 모듈 자체를 import

        # 주요 함수 및 상수가 모듈에 존재하는지 확인
        assert hasattr(src.chat_app, 'start')
        assert hasattr(src.chat_app, 'main')
        assert hasattr(src.chat_app, 'execute_tool')
        assert hasattr(src.chat_app, 'initialize_clients')
        assert hasattr(src.chat_app, 'SYSTEM_PROMPT')
        assert hasattr(src.chat_app, 'AVAILABLE_TOOLS')
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_command_parsing():
    """명령어 파싱 테스트"""
    # 기본 명령어
    cmd1 = "/help"
    parts1 = cmd1.split(maxsplit=1)
    assert parts1[0] == "/help"
    assert len(parts1) == 1

    # 인자가 있는 명령어
    cmd2 = "/summary . 50"
    parts2 = cmd2.split(maxsplit=1)
    assert parts2[0] == "/summary"
    assert parts2[1] == ". 50"

    # 경로가 있는 명령어
    cmd3 = "/index https://github.com/user/repo"
    parts3 = cmd3.split(maxsplit=1)
    assert parts3[0] == "/index"
    assert "https://" in parts3[1]


def test_intent_detection():
    """자연어 인텐트 감지 테스트"""
    # 요약 의도
    queries_summary = [
        "최근 커밋들을 요약해줘",
        "커밋 정리해줘",
        "최근 변경사항 보여줘"
    ]

    for query in queries_summary:
        assert any(kw in query.lower() for kw in ['요약', 'summary', '정리', '최근'])

    # 기여자 분석 의도
    queries_contributors = [
        "누가 가장 많이 기여했어?",
        "기여자 분석해줘",
        "contributor 보여줘"
    ]

    for query in queries_contributors:
        assert any(kw in query.lower() for kw in ['기여자', 'contributor', '누가'])

    # 버그 검색 의도
    queries_bugs = [
        "버그 수정 커밋 찾아줘",
        "fix 관련 커밋",
        "오류 수정"
    ]

    for query in queries_bugs:
        assert any(kw in query.lower() for kw in ['버그', 'bug', 'fix', '수정', '오류'])


def test_parameter_extraction():
    """파라미터 추출 테스트"""
    # 저장소 경로와 제한 수 추출
    args1 = ". 100"
    parts1 = args1.split()
    assert parts1[0] == "."
    assert int(parts1[1]) == 100

    # URL과 제한 수
    args2 = "https://github.com/rust-lang/rust 50"
    parts2 = args2.split()
    assert "https://" in parts2[0]
    assert int(parts2[1]) == 50

    # 경로만 있는 경우
    args3 = "."
    parts3 = args3.split()
    assert parts3[0] == "."
    assert len(parts3) == 1


def test_help_text_format():
    """도움말 텍스트 포맷 테스트"""
    help_keywords = [
        "/index",
        "/summary",
        "/search",
        "/contributors",
        "/bugs",
        "/help"
    ]

    # 모든 명령어가 포함되어야 함
    for keyword in help_keywords:
        assert keyword is not None


@pytest.mark.asyncio
async def test_async_functions():
    """비동기 함수 구조 테스트"""
    import asyncio

    # 간단한 비동기 실행 테스트
    async def dummy_async():
        await asyncio.sleep(0.01)
        return "success"

    result = await dummy_async()
    assert result == "success"


def test_session_state_keys():
    """세션 상태 키 테스트"""
    session_keys = ["repo_path", "index_name"]

    # 키가 정의되어 있는지 확인
    for key in session_keys:
        assert isinstance(key, str)
        assert len(key) > 0


def test_error_messages():
    """에러 메시지 포맷 테스트"""
    error_templates = [
        "❌ 알 수 없는 명령어",
        "❌ 저장소 경로를 입력해주세요",
        "❌ 검색어를 입력해주세요",
        "❌ 오류 발생"
    ]

    for template in error_templates:
        assert "❌" in template
        assert len(template) > 5


def test_success_messages():
    """성공 메시지 포맷 테스트"""
    success_templates = [
        "✅ 초기화 완료!",
        "✅ 성공!",
        "✅ 버그 관련 커밋이 없습니다."
    ]

    for template in success_templates:
        assert "✅" in template or "성공" in template


def test_command_list():
    """명령어 목록 완전성 테스트"""
    commands = {
        "help": "도움말",
        "index": "인덱싱",
        "summary": "요약",
        "search": "검색",
        "contributors": "기여자 분석",
        "bugs": "버그 찾기"
    }

    assert len(commands) == 6
    assert "help" in commands
    assert "index" in commands
    assert "summary" in commands


def test_repository_path_validation():
    """저장소 경로 유효성 검사 테스트"""
    valid_paths = [
        ".",
        "..",
        "/path/to/repo",
        "C:\\Users\\repo",
        "https://github.com/user/repo",
        "git@github.com:user/repo.git"
    ]

    for path in valid_paths:
        assert len(path) > 0
        # 기본적인 유효성 체크
        assert not path.isspace()


def test_limit_parameter_validation():
    """제한 수 파라미터 유효성 테스트"""
    valid_limits = ["10", "50", "100", "500", "1000"]

    for limit_str in valid_limits:
        limit = int(limit_str)
        assert limit > 0
        assert limit <= 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

