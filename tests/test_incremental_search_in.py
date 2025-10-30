"""
증분 인덱싱 로직 테스트 (search.in 기반 배치 확인)
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.indexer import CommitIndexer, normalize_repo_identifier


def test_get_existing_ids_for_candidates_basic():
    """
    후보 커밋 ID 중 실제로 존재하는 것만 반환하는지 확인
    """
    # Mock 클라이언트
    mock_search = Mock()
    mock_index = Mock()
    mock_openai = Mock()

    indexer = CommitIndexer(
        search_client=mock_search,
        index_client=mock_index,
        openai_client=mock_openai,
        index_name="test-index"
    )

    # 후보 5개 중 3개만 존재한다고 가정
    candidate_ids = ["commit_1", "commit_2", "commit_3", "commit_4", "commit_5"]
    existing_in_index = ["commit_1", "commit_3", "commit_5"]

    # Mock search.search 응답
    mock_results = [{"id": cid} for cid in existing_in_index]
    mock_search.search.return_value = iter(mock_results)

    # 실행
    repo_id = "test_repo_id"
    result = indexer._get_existing_ids_for_candidates(repo_id, candidate_ids)

    # 검증
    assert result == {"commit_1", "commit_3", "commit_5"}
    assert "commit_2" not in result
    assert "commit_4" not in result

    # search.in 필터가 제대로 호출되었는지 확인
    mock_search.search.assert_called_once()
    call_args = mock_search.search.call_args
    assert "search.in(id," in call_args[1]["filter"]


def test_get_existing_ids_for_candidates_empty():
    """
    후보가 비어있으면 빈 set 반환
    """
    mock_search = Mock()
    mock_index = Mock()
    mock_openai = Mock()

    indexer = CommitIndexer(
        search_client=mock_search,
        index_client=mock_index,
        openai_client=mock_openai,
        index_name="test-index"
    )

    result = indexer._get_existing_ids_for_candidates("repo_id", [])

    assert result == set()
    mock_search.search.assert_not_called()


def test_get_existing_ids_for_candidates_chunking():
    """
    대용량(800개 초과) 후보가 청크로 나뉘어 처리되는지 확인
    """
    mock_search = Mock()
    mock_index = Mock()
    mock_openai = Mock()

    indexer = CommitIndexer(
        search_client=mock_search,
        index_client=mock_index,
        openai_client=mock_openai,
        index_name="test-index"
    )

    # 1000개 후보 생성
    candidate_ids = [f"commit_{i}" for i in range(1000)]

    # 첫 800개 청크에서 400개, 나머지 200개 청크에서 100개 존재
    def mock_search_side_effect(*args, **kwargs):
        filter_expr = kwargs.get("filter", "")
        if "commit_0," in filter_expr:  # 첫 청크
            return iter([{"id": f"commit_{i}"} for i in range(0, 400)])
        else:  # 두 번째 청크
            return iter([{"id": f"commit_{i}"} for i in range(800, 900)])

    mock_search.search.side_effect = mock_search_side_effect

    # 실행
    result = indexer._get_existing_ids_for_candidates("repo_id", candidate_ids, chunk_size=800)

    # 검증: 2번 호출되어야 함 (800 + 200)
    assert mock_search.search.call_count == 2
    assert len(result) == 500  # 400 + 100


def test_incremental_indexing_skips_existing():
    """
    증분 인덱싱이 기존 커밋을 제대로 스킵하는지 통합 확인
    """
    from unittest.mock import patch

    mock_search = Mock()
    mock_index = Mock()
    mock_openai = Mock()

    indexer = CommitIndexer(
        search_client=mock_search,
        index_client=mock_index,
        openai_client=mock_openai,
        index_name="test-index"
    )

    # Mock DocumentGenerator - 5개 커밋 반환
    mock_commits = [
        {"id": f"commit_{i}", "message": f"Message {i}", "author": "Test",
         "date": "2024-01-01T00:00:00Z", "files": [], "parents": []}
        for i in range(5)
    ]

    with patch('src.indexer.DocumentGenerator') as mock_gen_class:
        mock_gen = Mock()
        mock_gen.get_commits.return_value = mock_commits
        mock_gen.close.return_value = None
        mock_gen_class.return_value = mock_gen

        # 5개 중 2개(commit_1, commit_3)만 이미 인덱싱되어 있다고 가정
        existing_ids = ["commit_1", "commit_3"]
        mock_search.search.return_value = iter([{"id": cid} for cid in existing_ids])

        # Mock embed_texts
        with patch('src.indexer.embed_texts') as mock_embed:
            mock_embed.return_value = [[0.1] * 1536] * 3  # 3개만 임베딩됨

            # Mock upload_documents
            mock_result = [Mock(succeeded=True) for _ in range(3)]
            mock_search.upload_documents.return_value = mock_result

            # 실행
            count = indexer.index_repository(
                repo_path="test/repo",
                limit=5,
                skip_existing=True
            )

            # 검증: 5개 중 2개 스킵, 3개만 인덱싱
            assert count == 3

            # embed_texts가 3개만 호출되었는지 확인
            mock_embed.assert_called_once()
            assert len(mock_embed.call_args[0][0]) == 3

            # upload_documents도 3개만 호출
            mock_search.upload_documents.assert_called_once()
            uploaded_docs = mock_search.upload_documents.call_args[1]["documents"]
            assert len(uploaded_docs) == 3

            # 스킵된 커밋이 업로드에 포함되지 않았는지 확인
            uploaded_ids = {doc["id"] for doc in uploaded_docs}
            assert "commit_1" not in uploaded_ids
            assert "commit_3" not in uploaded_ids
            assert "commit_0" in uploaded_ids
            assert "commit_2" in uploaded_ids
            assert "commit_4" in uploaded_ids


def test_normalize_repo_identifier_consistency():
    """
    같은 저장소는 항상 같은 repo_id를 반환하는지 확인
    """
    path1 = "https://github.com/user/repo"
    path2 = "https://github.com/user/repo.git"
    path3 = "https://github.com/user/repo/"

    id1 = normalize_repo_identifier(path1)
    id2 = normalize_repo_identifier(path2)
    id3 = normalize_repo_identifier(path3)

    # 모두 동일한 repo_id여야 함
    assert id1 == id2 == id3
    assert len(id1) == 16  # 해시 길이 확인


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

