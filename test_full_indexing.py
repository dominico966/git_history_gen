#!/usr/bin/env python
"""원격 저장소 인덱싱 전체 테스트"""
import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from src.indexer import CommitIndexer

print("=" * 80)
print("원격 저장소 인덱싱 테스트")
print("=" * 80)

# Azure 클라이언트 초기화
search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
search_key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")

openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

search_client = SearchClient(
    endpoint=search_endpoint,
    index_name=index_name,
    credential=AzureKeyCredential(search_key)
)

index_client = SearchIndexClient(
    endpoint=search_endpoint,
    credential=AzureKeyCredential(search_key)
)

# 인덱서 생성
indexer = CommitIndexer(
    search_client=search_client,
    index_client=index_client,
    openai_client=openai_client,
    index_name=index_name
)

# 인덱스 생성 (없으면)
print("\n📋 인덱스 생성 중...")
try:
    indexer.create_index_if_not_exists()
    print("✅ 인덱스 준비 완료")
except Exception as e:
    print(f"❌ 인덱스 생성 실패: {e}")
    sys.exit(1)

# 테스트할 저장소
test_repo = "https://github.com/chromiumembedded/cef"

print(f"\n📦 인덱싱 테스트: {test_repo}")
print(f"   (limit=10으로 제한)")

try:
    indexed_count = indexer.index_repository(
        repo_path=test_repo,
        limit=10,
        skip_existing=True
    )
    print(f"\n✅ 인덱싱 완료: {indexed_count}개 문서")
except Exception as e:
    print(f"\n❌ 인덱싱 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)

