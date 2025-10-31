#!/usr/bin/env python
"""전체 워크플로우 테스트"""
import sys
import os
import json
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
from src.tools import get_commit_count
from src.indexer import CommitIndexer, normalize_repo_identifier

print("=" * 80)
print("전체 워크플로우 테스트: chromiumembedded/cef")
print("=" * 80)

repo_url = "https://github.com/chromiumembedded/cef"

# Step 1: 커밋 개수 확인
print("\n📊 Step 1: 커밋 개수 확인")
result = get_commit_count(repo_path=repo_url)
print(json.dumps(result, ensure_ascii=False, indent=2))

if not result.get("has_commits"):
    print("❌ 커밋이 없거나 접근 실패")
    sys.exit(1)

commit_count = result["commit_count"]
print(f"✅ 총 {commit_count}개 커밋 확인")

# Step 2: 인덱싱
print("\n📝 Step 2: 인덱싱 (limit=5)")

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

indexer = CommitIndexer(
    search_client=search_client,
    index_client=index_client,
    openai_client=openai_client,
    index_name=index_name
)

indexer.create_index_if_not_exists()

try:
    indexed_count = indexer.index_repository(
        repo_path=repo_url,
        limit=5,
        skip_existing=False  # 중복도 다시 인덱싱 (테스트용)
    )
    print(f"✅ {indexed_count}개 커밋 인덱싱 완료")
except Exception as e:
    print(f"❌ 인덱싱 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: 검색 테스트
print("\n🔍 Step 3: 검색 테스트")
repo_id = normalize_repo_identifier(repo_url)
print(f"Repo ID: {repo_id}")

# 검색 쿼리
filter_expr = f"repo_id eq '{repo_id}'"
results = search_client.search(
    search_text="*",
    filter=filter_expr,
    select=["id", "message", "author", "date"],
    top=3
)

print("\n최근 인덱싱된 커밋:")
for r in results:
    print(f"  - {r['message'][:50]}... (by {r['author']})")

print("\n" + "=" * 80)
print("✅ 전체 워크플로우 테스트 성공!")
print("=" * 80)

