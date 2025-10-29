import os
import logging
from typing import Tuple
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def initialize_models() -> Tuple[AzureOpenAI, SearchClient, SearchIndexClient]:
    """
    Azure OpenAI 클라이언트와 Azure AI Search 클라이언트를 초기화합니다.

    Returns:
        Tuple[AzureOpenAI, SearchClient, SearchIndexClient]:
        (OpenAI 클라이언트, 검색 클라이언트, 인덱스 클라이언트)

    Raises:
        ValueError: 필수 환경변수가 설정되지 않은 경우
    """
    try:
        # 환경변수 검증
        required_vars = [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_SEARCH_ENDPOINT",
            "AZURE_SEARCH_INDEX_NAME",
            "AZURE_SEARCH_API_KEY"
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Azure OpenAI client
        logger.info("Initializing Azure OpenAI client...")
        openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

        # Azure AI Search client
        logger.info("Initializing Azure AI Search client...")
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY"))

        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
            credential=search_credential
        )

        # Search Index Client for index management
        index_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=search_credential
        )

        logger.info("✓ All clients initialized successfully")
        return openai_client, search_client, index_client

    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
        raise
