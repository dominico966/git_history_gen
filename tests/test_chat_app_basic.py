"""
chat_app.py 기본 기능 테스트
"""

import pytest
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# src 모듈을 import 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


def test_environment_variables():
    """필수 환경 변수가 설정되어 있는지 확인"""
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_INDEX_NAME",
        "AZURE_SEARCH_API_KEY"
    ]

    for var in required_vars:
        assert os.getenv(var), f"환경 변수 {var}가 설정되지 않았습니다."


def test_system_prompt_structure():
    """시스템 프롬프트가 구조화된 형태인지 확인"""
    from src.chat_app import SYSTEM_PROMPT_PARTS, SYSTEM_PROMPT

    # 여러 줄 문자열이 아닌 리스트로 관리
    assert isinstance(SYSTEM_PROMPT_PARTS, list)
    assert len(SYSTEM_PROMPT_PARTS) > 0

    # 최종 프롬프트는 문자열
    assert isinstance(SYSTEM_PROMPT, str)
    assert len(SYSTEM_PROMPT) > 0

    # 여러 줄 문자열 사용 여부 확인
    assert '"""' not in SYSTEM_PROMPT
    assert "'''" not in SYSTEM_PROMPT


def test_tools_structure():
    """도구 정의가 올바른 구조인지 확인"""
    from src.chat_app import AVAILABLE_TOOLS

    assert isinstance(AVAILABLE_TOOLS, list)
    assert len(AVAILABLE_TOOLS) > 0

    # 필수 도구 확인
    tool_names = [tool["function"]["name"] for tool in AVAILABLE_TOOLS]
    required_tools = ["set_current_repository", "index_repository", "get_commit_diff"]

    for req_tool in required_tools:
        assert req_tool in tool_names, f"{req_tool} 도구가 없습니다"

    for tool in AVAILABLE_TOOLS:
        assert "type" in tool
        assert tool["type"] == "function"
        assert "function" in tool

        func = tool["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func

    print(f"✓ 총 {len(AVAILABLE_TOOLS)}개 도구 확인됨")
    print(f"✓ 도구 목록: {', '.join(tool_names)}")


def test_initialize_clients():
    """클라이언트 초기화 테스트"""
    from src.chat_app import initialize_clients

    try:
        openai_client, search_client, index_client = initialize_clients()

        assert openai_client is not None
        assert search_client is not None
        assert index_client is not None

        print("✓ 클라이언트 초기화 성공 (OpenAI, Search, Index)")

    except Exception as e:
        pytest.fail(f"클라이언트 초기화 실패: {e}")


@pytest.mark.asyncio
async def test_execute_tool_basic():
    """도구 실행 기본 테스트"""
    from src.chat_app import execute_tool, initialize_clients

    openai_client, search_client, index_client = initialize_clients()

    # GitHub 저장소 검색 테스트
    result = await execute_tool(
        tool_name="search_github_repo",
        arguments={"query": "tauri", "max_results": 2},
        openai_client=openai_client,
        search_client=search_client,
        index_client=index_client
    )

    assert result is not None
    assert len(result) > 0
    print(f"✓ 도구 실행 성공: {result[:200]}...")


def test_max_limits():
    """최대값 제한 상수가 설정되어 있는지 확인"""
    from src.chat_app import (
        MAX_COMMIT_LIMIT,
        MAX_SEARCH_TOP,
        MAX_CONTRIBUTOR_LIMIT,
        MAX_TOOL_RESULT_DISPLAY,
        MAX_TOOL_RESULT_TO_LLM,
        MAX_CONVERSATION_MESSAGES
    )

    assert MAX_COMMIT_LIMIT > 0
    assert MAX_SEARCH_TOP > 0
    assert MAX_CONTRIBUTOR_LIMIT > 0
    assert MAX_TOOL_RESULT_DISPLAY > 0
    assert MAX_TOOL_RESULT_TO_LLM > 0
    assert MAX_CONVERSATION_MESSAGES > 0

    print(f"✓ MAX_COMMIT_LIMIT: {MAX_COMMIT_LIMIT}")
    print(f"✓ MAX_SEARCH_TOP: {MAX_SEARCH_TOP}")
    print(f"✓ MAX_CONTRIBUTOR_LIMIT: {MAX_CONTRIBUTOR_LIMIT}")
    print(f"✓ MAX_TOOL_RESULT_DISPLAY: {MAX_TOOL_RESULT_DISPLAY}")
    print(f"✓ MAX_TOOL_RESULT_TO_LLM: {MAX_TOOL_RESULT_TO_LLM}")
    print(f"✓ MAX_CONVERSATION_MESSAGES: {MAX_CONVERSATION_MESSAGES}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

