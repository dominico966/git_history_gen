"""
실제 기능 테스트 스크립트
- embedding 모델: text-embedding-3-small
- LLM 모델: gpt-4.1-mini
- 문서 메타데이터 추가 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import os
import logging
import pytest
from dotenv import load_dotenv
from src.agent import initialize_models
from src.indexer import CommitIndexer
from src.document_generator import DocumentGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pytest fixtures
@pytest.fixture(scope="module")
def models():
    """모델 초기화 fixture"""
    load_dotenv()
    llm_client, search_client, index_client = initialize_models()
    return llm_client, search_client, index_client

@pytest.fixture(scope="module")
def llm_client(models):
    """LLM 클라이언트 fixture"""
    return models[0]

@pytest.fixture(scope="module")
def search_client(models):
    """검색 클라이언트 fixture"""
    return models[1]

@pytest.fixture(scope="module")
def index_client(models):
    """인덱스 클라이언트 fixture"""
    return models[2]

def test_models(models):
    """모델 초기화 테스트"""
    logger.info("=" * 60)
    logger.info("1. 모델 초기화 테스트")
    logger.info("=" * 60)

    llm_client, search_client, index_client = models

    llm_model = os.getenv("AZURE_OPENAI_MODEL")
    embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")

    logger.info(f"LLM Model: {llm_model}")
    logger.info(f"Embedding Model: {embedding_model}")

    assert llm_client is not None, "LLM 클라이언트가 None입니다"
    assert search_client is not None, "검색 클라이언트가 None입니다"
    assert index_client is not None, "인덱스 클라이언트가 None입니다"

    logger.info("✓ 모델 초기화 성공")

def test_document_generation(repo_path: str = "."):
    """문서 생성 및 메타데이터 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("2. 문서 생성 및 메타데이터 테스트")
    logger.info("=" * 60)

    doc_gen = DocumentGenerator(repo_path)

    # 최근 5개 커밋 가져오기
    commits = doc_gen.get_commits(limit=5)
    logger.info(f"최근 {len(commits)}개 커밋 분석 시작...")

    assert len(commits) > 0, "커밋이 없습니다"

    for i, commit_data in enumerate(commits, 1):
        logger.info(f"\n--- 커밋 {i}/{len(commits)} ---")
        logger.info(f"SHA: {commit_data['id'][:8]}")
        logger.info(f"Message: {commit_data['message'].strip()[:50]}...")

        # 기본 정보
        logger.info(f"Author: {commit_data['author']}")
        logger.info(f"Date: {commit_data['date']}")
        logger.info(f"Files Changed: {len(commit_data['files'])}")

        # 기본 필드 검증
        assert 'id' in commit_data, "커밋 ID가 없습니다"
        assert 'message' in commit_data, "커밋 메시지가 없습니다"
        assert 'author' in commit_data, "작성자 정보가 없습니다"
        assert 'date' in commit_data, "날짜 정보가 없습니다"
        assert 'files' in commit_data, "파일 정보가 없습니다"

        # 메타데이터 확인
        if 'change_context' in commit_data:
            context = commit_data['change_context']
            logger.info(f"✓ Change Context 생성됨:")
            logger.info(f"  - Files by Category: {context.get('file_categories', {})}")
            logger.info(f"  - Modified Files: {context.get('modified_files', [])[:3]}...")

        if 'function_analysis' in commit_data:
            analysis = commit_data['function_analysis']
            logger.info(f"✓ Function Analysis 생성됨:")
            logger.info(f"  - Modified Functions: {len(analysis.get('modified_functions', []))}")
            logger.info(f"  - Added Functions: {len(analysis.get('added_functions', []))}")
            logger.info(f"  - Removed Functions: {len(analysis.get('removed_functions', []))}")
            logger.info(f"  - Complexity: {analysis.get('code_complexity_hint', 'unknown')}")

        if 'relation_to_previous' in commit_data and commit_data['relation_to_previous']:
            relation = commit_data['relation_to_previous']
            logger.info(f"✓ Relation to Previous 생성됨:")
            logger.info(f"  - Related Files: {len(relation.get('related_files', []))}")
            logger.info(f"  - Common Files: {relation.get('common_files', [])[:3]}")
        else:
            logger.info(f"⚠ Relation to Previous: None (첫 커밋)")

    logger.info("\n✓ 문서 생성 테스트 성공")
    doc_gen.close()

def test_embedding(llm_client):
    """임베딩 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("3. 임베딩 모델 테스트")
    logger.info("=" * 60)

    from src.embedding import embed_texts

    test_texts = [
        "Add new feature for user authentication",
        "Fix bug in payment processing",
        "Update documentation for API endpoints"
    ]

    logger.info(f"테스트 텍스트 {len(test_texts)}개 임베딩 중...")
    embeddings = embed_texts(test_texts, llm_client)

    assert len(embeddings) == len(test_texts), f"임베딩 수가 일치하지 않습니다: {len(embeddings)} != {len(test_texts)}"
    assert len(embeddings) > 0, "임베딩이 생성되지 않았습니다"
    assert len(embeddings[0]) > 0, "임베딩 벡터가 비어있습니다"

    logger.info(f"✓ 임베딩 성공:")
    logger.info(f"  - 벡터 수: {len(embeddings)}")
    logger.info(f"  - 벡터 차원: {len(embeddings[0])}")


def test_indexing(llm_client, search_client, index_client, repo_path: str = ".", limit: int = 10):
    """인덱싱 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("4. 인덱싱 테스트")
    logger.info("=" * 60)

    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")

    indexer = CommitIndexer(
        search_client=search_client,
        index_client=index_client,
        openai_client=llm_client,
        index_name=index_name
    )

    # 기존 인덱스 삭제 (새로운 스키마 적용을 위해)
    try:
        logger.info(f"기존 인덱스 '{index_name}' 삭제 시도...")
        indexer.delete_index()
        logger.info("✓ 기존 인덱스 삭제 완료")
    except Exception as e:
        logger.info(f"인덱스 삭제 건너뛰기 (인덱스가 없거나 이미 삭제됨): {e}")

    logger.info(f"인덱스 '{index_name}' 생성 중...")
    indexer.create_index_if_not_exists(vector_dimensions=1536)
    logger.info("✓ 인덱스 생성/확인 완료")

    logger.info(f"\n최근 {limit}개 커밋 인덱싱 중...")
    count = indexer.index_repository(repo_path, limit=limit)

    assert count >= 0, f"인덱싱된 커밋 수가 음수입니다: {count}"
    logger.info(f"✓ {count}개 커밋 인덱싱 성공")


def test_search(search_client, llm_client):
    """검색 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("5. 검색 테스트")
    logger.info("=" * 60)

    from src.tools import search_commits

    test_queries = [
        "bug fix",
        "feature",
        "documentation"
    ]

    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        results = search_commits(query, search_client, llm_client, top=3)

        assert isinstance(results, list), f"검색 결과가 리스트가 아닙니다: {type(results)}"
        logger.info(f"✓ 검색 결과: {len(results)}개")

        for i, result in enumerate(results, 1):
            assert 'message' in result, f"검색 결과 {i}에 message가 없습니다"
            logger.info(f"  {i}. {result.get('message', '')[:50]}... (score: {result.get('score', 0):.2f})")

# 독립 실행용 함수 (pytest에서는 실행되지 않음)
def run_all_tests():
    """모든 테스트를 순차적으로 실행 (독립 실행용)"""
    logger.info("\n" + "=" * 60)
    logger.info("Git History Generator - 실제 기능 테스트")
    logger.info("=" * 60)

    load_dotenv()

    try:
        # 1. 모델 초기화
        logger.info("=" * 60)
        logger.info("1. 모델 초기화 테스트")
        logger.info("=" * 60)
        llm_client, search_client, index_client = initialize_models()

        llm_model = os.getenv("AZURE_OPENAI_MODEL")
        embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")
        logger.info(f"LLM Model: {llm_model}")
        logger.info(f"Embedding Model: {embedding_model}")
        logger.info("✓ 모델 초기화 성공")

        # 2. 문서 생성 테스트
        test_document_generation()

        # 3. 임베딩 테스트
        test_embedding(llm_client)

        # 4. 인덱싱 테스트
        test_indexing(llm_client, search_client, index_client, limit=5)

        # 5. 검색 테스트
        test_search(search_client, llm_client)

        logger.info("\n" + "=" * 60)
        logger.info("✓ 모든 테스트 완료!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n✗ 테스트 실패: {e}", exc_info=True)
        return 1

    return 0

if __name__ == "__main__":
    exit(run_all_tests())

