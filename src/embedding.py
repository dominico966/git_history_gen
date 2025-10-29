import os
import asyncio
from typing import List
from openai import AzureOpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "20"))
EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# 임베딩 모델 로드 확인
logger.info(f"Using embedding model: {EMBEDDING_MODEL}")


async def embed_texts_async(texts: List[str], openai_client: AzureOpenAI) -> List[List[float]]:
    """
    텍스트 리스트를 비동기로 임베딩합니다.
    배치 단위로 처리하여 API 호출을 최소화합니다.

    Args:
        texts: 임베딩할 텍스트 리스트
        openai_client: Azure OpenAI 클라이언트

    Returns:
        List[List[float]]: 임베딩 벡터 리스트

    Raises:
        Exception: 임베딩 실패 시
    """
    if not texts:
        return []

    embeddings: List[List[float]] = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    logger.info(f"Embedding {len(texts)} texts in {total_batches} batches (batch size: {BATCH_SIZE})")

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        try:
            logger.debug(f"Processing batch {batch_num}/{total_batches}")

            # 비동기 실행을 위해 run_in_executor 사용
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: openai_client.embeddings.create(
                    input=batch,
                    model=EMBEDDING_MODEL
                )
            )

            batch_embeddings = [data.embedding for data in response.data]
            embeddings.extend(batch_embeddings)

            logger.debug(f"✓ Batch {batch_num}/{total_batches} completed ({len(batch_embeddings)} embeddings)")

        except Exception as e:
            logger.error(f"Error embedding batch {batch_num}: {e}")
            # 실패한 배치에 대해 빈 임베딩 추가
            embeddings.extend([[] for _ in batch])

    logger.info(f"✓ Embedding completed: {len(embeddings)} vectors")
    return embeddings


def embed_texts(texts: List[str], openai_client: AzureOpenAI) -> List[List[float]]:
    """
    텍스트 리스트를 임베딩합니다 (동기 버전).
    배치 단위로 처리하여 API 호출을 최소화합니다.

    Args:
        texts: 임베딩할 텍스트 리스트
        openai_client: Azure OpenAI 클라이언트

    Returns:
        List[List[float]]: 임베딩 벡터 리스트
    """
    if not texts:
        return []

    embeddings: List[List[float]] = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    logger.info(f"Embedding {len(texts)} texts in {total_batches} batches (batch size: {BATCH_SIZE})")

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        try:
            logger.debug(f"Processing batch {batch_num}/{total_batches}")

            response = openai_client.embeddings.create(
                input=batch,
                model=EMBEDDING_MODEL
            )

            batch_embeddings = [data.embedding for data in response.data]
            embeddings.extend(batch_embeddings)

            logger.debug(f"✓ Batch {batch_num}/{total_batches} completed ({len(batch_embeddings)} embeddings)")

        except Exception as e:
            logger.error(f"Error embedding batch {batch_num}: {e}")
            # 실패한 배치에 대해 빈 임베딩 추가
            embeddings.extend([[] for _ in batch])

    logger.info(f"✓ Embedding completed: {len(embeddings)} vectors")
    return embeddings
