"""
embedding.py 테스트
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.embedding import embed_texts, embed_texts_async
import asyncio


def test_embed_texts_empty_list():
    """빈 리스트에 대한 테스트"""
    mock_client = Mock()
    result = embed_texts([], mock_client)
    assert result == []
    mock_client.embeddings.create.assert_not_called()


def test_embed_texts_success():
    """정상적인 임베딩 테스트"""
    mock_client = Mock()

    # Mock response
    mock_response = Mock()
    mock_data = Mock()
    mock_data.embedding = [0.1, 0.2, 0.3]
    mock_response.data = [mock_data]

    mock_client.embeddings.create.return_value = mock_response

    texts = ["test text"]
    result = embed_texts(texts, mock_client)

    assert len(result) == 1
    assert result[0] == [0.1, 0.2, 0.3]
    mock_client.embeddings.create.assert_called_once()


def test_embed_texts_batch_processing():
    """배치 처리 테스트"""
    mock_client = Mock()

    # Mock response - 각 아이템에 대해 개별 임베딩 반환
    def create_mock_response(batch_size):
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2]) for _ in range(batch_size)]
        return mock_response

    # side_effect로 각 호출마다 적절한 크기의 응답 반환
    mock_client.embeddings.create.side_effect = [
        create_mock_response(20),  # 첫 번째 배치 (20개)
        create_mock_response(5),   # 두 번째 배치 (5개)
    ]

    # Test with multiple batches (assuming batch size is 20)
    texts = [f"text_{i}" for i in range(25)]
    result = embed_texts(texts, mock_client)

    # Should call API twice (batch 1: 20 items, batch 2: 5 items)
    assert mock_client.embeddings.create.call_count == 2
    assert len(result) == 25


def test_embed_texts_error_handling():
    """에러 처리 테스트"""
    mock_client = Mock()
    mock_client.embeddings.create.side_effect = Exception("API Error")

    texts = ["test"]
    result = embed_texts(texts, mock_client)

    # Should return empty embedding for failed items
    assert len(result) == 1
    assert result[0] == []


@pytest.mark.asyncio
async def test_embed_texts_async():
    """비동기 임베딩 테스트"""
    mock_client = Mock()

    # Mock response
    mock_response = Mock()
    mock_data = Mock()
    mock_data.embedding = [0.5, 0.6, 0.7]
    mock_response.data = [mock_data]

    mock_client.embeddings.create.return_value = mock_response

    texts = ["async test"]
    result = await embed_texts_async(texts, mock_client)

    assert len(result) == 1
    assert result[0] == [0.5, 0.6, 0.7]

