"""
증분 인덱싱 로직 테스트 - MAX_COMMIT_LIMIT cap이 증분 인덱싱을 방해하지 않는지 확인
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio


@pytest.mark.asyncio
async def test_incremental_indexing_not_capped_too_early():
    """
    증분 인덱싱 로직이 MAX_COMMIT_LIMIT cap 이전에 실행되는지 확인

    시나리오:
    - 전체 커밋: 1,124개
    - 이미 인덱싱: 200개
    - 사용자 요청: limit=1124
    - 증분 인덱싱: 1124 - 200 = 924개 추가 필요
    - 실제 인덱싱: 924개 (MAX_COMMIT_LIMIT=2000 이내)
    """
    from src.chat_app import execute_tool, MAX_COMMIT_LIMIT

    # Mock 클라이언트
    mock_openai = Mock()
    mock_search = Mock()
    mock_index = Mock()

    # Mock search_client.search (기존 인덱싱 개수 조회)
    mock_existing_commits = [{"id": f"commit_{i}"} for i in range(200)]
    mock_search.search.return_value = iter(mock_existing_commits)

    # Mock indexer
    with patch('src.chat_app.CommitIndexer') as mock_indexer_class:
        mock_indexer = Mock()
        mock_indexer.create_index_if_not_exists.return_value = None
        mock_indexer.index_repository.return_value = 924  # 증분 인덱싱 결과
        mock_indexer_class.return_value = mock_indexer

        with patch('src.chat_app.cl'):
            # 도구 실행
            result = await execute_tool(
                tool_name="index_repository",
                arguments={
                    "repo_path": "https://github.com/Chainlit/chainlit",
                    "limit": 1124,  # 전체 커밋 수
                    "skip_existing": True
                },
                openai_client=mock_openai,
                search_client=mock_search,
                index_client=mock_index
            )

            # 검증
            # 1. indexer.index_repository가 호출되었는지
            assert mock_indexer.index_repository.called

            # 2. 호출된 limit이 924인지 (증분 인덱싱)
            call_args = mock_indexer.index_repository.call_args
            assert call_args[1]["limit"] == 924, f"Expected limit=924, got {call_args[1]['limit']}"

            # 3. skip_offset이 200인지
            assert call_args[1]["skip_offset"] == 200, f"Expected skip_offset=200, got {call_args[1]['skip_offset']}"


@pytest.mark.asyncio
async def test_already_enough_commits():
    """
    이미 충분한 커밋이 있을 때 조기 종료되는지 확인

    시나리오:
    - 전체 커밋: 1,124개
    - 이미 인덱싱: 200개
    - 사용자 요청: limit=200
    - 결과: 추가 인덱싱 없이 조기 종료
    """
    from src.chat_app import execute_tool

    # Mock 클라이언트
    mock_openai = Mock()
    mock_search = Mock()
    mock_index = Mock()

    # Mock search_client.search (기존 인덱싱 개수 조회)
    mock_existing_commits = [{"id": f"commit_{i}"} for i in range(200)]
    mock_search.search.return_value = iter(mock_existing_commits)

    # Mock indexer
    with patch('src.chat_app.CommitIndexer') as mock_indexer_class:
        mock_indexer = Mock()
        mock_indexer.create_index_if_not_exists.return_value = None
        mock_indexer_class.return_value = mock_indexer

        with patch('src.chat_app.cl'):
            # 도구 실행
            result = await execute_tool(
                tool_name="index_repository",
                arguments={
                    "repo_path": "https://github.com/Chainlit/chainlit",
                    "limit": 200,  # 이미 충분함
                    "skip_existing": True
                },
                openai_client=mock_openai,
                search_client=mock_search,
                index_client=mock_index
            )

            # 검증: index_repository가 호출되지 않았어야 함
            assert not mock_indexer.index_repository.called, "index_repository should not be called when enough commits exist"
            assert "이미" in result, f"Expected early return message, got: {result}"


@pytest.mark.asyncio
async def test_cap_applied_after_incremental():
    """
    MAX_COMMIT_LIMIT cap이 증분 인덱싱 계산 이후에만 적용되는지 확인

    시나리오:
    - 전체 커밋: 3,000개
    - 이미 인덱싱: 100개
    - 사용자 요청: limit=3000
    - 증분 계산: 3000 - 100 = 2900개 추가 필요
    - cap 적용: 2900 → 2000 (MAX_COMMIT_LIMIT)
    """
    from src.chat_app import execute_tool

    # Mock 클라이언트
    mock_openai = Mock()
    mock_search = Mock()
    mock_index = Mock()

    # Mock search_client.search (기존 인덱싱 개수 조회)
    mock_existing_commits = [{"id": f"commit_{i}"} for i in range(100)]
    mock_search.search.return_value = iter(mock_existing_commits)

    # Mock indexer
    with patch('src.chat_app.CommitIndexer') as mock_indexer_class:
        mock_indexer = Mock()
        mock_indexer.create_index_if_not_exists.return_value = None
        mock_indexer.index_repository.return_value = 2000  # cap된 결과
        mock_indexer_class.return_value = mock_indexer

        with patch('src.chat_app.cl'):
            # Mock UI 승인
            with patch('src.chat_app.cl.AskActionMessage') as mock_ask:
                mock_response = Mock()
                mock_response.get.return_value = {"action": "proceed"}
                mock_ask_instance = Mock()
                mock_ask_instance.send = asyncio.coroutine(lambda: mock_response)
                mock_ask.return_value = mock_ask_instance

                with patch('src.chat_app.cl.Message') as mock_message:
                    mock_msg = Mock()
                    mock_msg.send = asyncio.coroutine(lambda: None)
                    mock_msg.update = asyncio.coroutine(lambda: None)
                    mock_message.return_value = mock_msg

                    with patch('src.chat_app.get_commit_count') as mock_count:
                        mock_count.return_value = {"commit_count": 3000, "has_commits": True}

                        # 도구 실행
                        result = await execute_tool(
                            tool_name="index_repository",
                            arguments={
                                "repo_path": "https://github.com/test/repo",
                                "limit": 3000,
                                "skip_existing": True
                            },
                            openai_client=mock_openai,
                            search_client=mock_search,
                            index_client=mock_index
                        )

                        # 검증: indexer.index_repository가 호출되었는지
                        assert mock_indexer.index_repository.called

                        # 호출된 limit 확인 (2900이 cap되어 2000이 되어야 함)
                        call_args = mock_indexer.index_repository.call_args
                        called_limit = call_args[1]["limit"]

                        # 2900이 MAX_COMMIT_LIMIT(2000)으로 cap되었는지 확인
                        assert called_limit == 2000, f"Expected limit=2000 (capped from 2900), got {called_limit}"

                        # skip_offset이 100인지 확인
                        assert call_args[1]["skip_offset"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

