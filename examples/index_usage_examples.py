"""
Azure AI Search Index 활용 예제 스크립트
실제 사용 시나리오를 보여주는 예제 코드
"""

import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI

from src.indexer import CommitIndexer
from src.index_manager import IndexManager, format_index_statistics
from src.tools import search_commits

load_dotenv()


def initialize_clients():
    """클라이언트 초기화"""
    openai_client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    search_credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY"))

    search_client = SearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        credential=search_credential
    )

    index_client = SearchIndexClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        credential=search_credential
    )

    return openai_client, search_client, index_client


def example_1_basic_indexing():
    """예제 1: 기본 인덱싱"""
    print("=" * 80)
    print("예제 1: 기본 인덱싱")
    print("=" * 80)

    openai_client, search_client, index_client = initialize_clients()

    indexer = CommitIndexer(
        search_client=search_client,
        index_client=index_client,
        openai_client=openai_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    # 인덱스 생성 (없으면)
    indexer.create_index_if_not_exists()

    # 저장소 인덱싱 (최근 100개 커밋)
    repo_path = "https://github.com/chainlit/chainlit"
    print(f"\n저장소 인덱싱 중: {repo_path}")

    indexed_count = indexer.index_repository(
        repo_path=repo_path,
        limit=100,
        skip_existing=True
    )

    print(f"✓ {indexed_count}개 커밋 인덱싱 완료\n")


def example_2_index_statistics():
    """예제 2: 인덱스 통계 확인"""
    print("=" * 80)
    print("예제 2: 인덱스 통계 확인")
    print("=" * 80)

    _, search_client, index_client = initialize_clients()

    manager = IndexManager(
        search_client=search_client,
        index_client=index_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    # 통계 조회
    stats = manager.get_index_statistics()
    formatted = format_index_statistics(stats)
    print(f"\n{formatted}\n")


def example_3_list_repositories():
    """예제 3: 인덱싱된 저장소 목록"""
    print("=" * 80)
    print("예제 3: 인덱싱된 저장소 목록")
    print("=" * 80)

    _, search_client, index_client = initialize_clients()

    manager = IndexManager(
        search_client=search_client,
        index_client=index_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    # 저장소 목록 조회
    repos = manager.list_indexed_repositories()

    print(f"\n📁 인덱싱된 저장소: {len(repos)}개\n")
    for repo in repos:
        print(f"- {repo['repository_path']}")
        print(f"  Repo ID: {repo['repo_id']}")
        print(f"  커밋 수: {repo['commit_count']}")
        print()


def example_4_search_commits():
    """예제 4: 커밋 검색"""
    print("=" * 80)
    print("예제 4: 커밋 검색")
    print("=" * 80)

    openai_client, search_client, _ = initialize_clients()

    # 자연어 검색
    query = "authentication login"
    print(f"\n검색 쿼리: '{query}'\n")

    results = search_commits(
        query=query,
        search_client=search_client,
        openai_client=openai_client,
        top=5
    )

    print(f"검색 결과: {len(results)}개\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result['date'][:10]}] {result['author']}")
        print(f"   {result['message'][:80]}...")
        print(f"   Score: {result['score']:.2f}")
        print(f"   Repository: {result.get('repository', 'N/A')}")
        print()


def example_5_repository_info():
    """예제 5: 특정 저장소 정보 조회"""
    print("=" * 80)
    print("예제 5: 특정 저장소 정보 조회")
    print("=" * 80)

    _, search_client, index_client = initialize_clients()

    manager = IndexManager(
        search_client=search_client,
        index_client=index_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    # 먼저 저장소 목록 조회
    repos = manager.list_indexed_repositories()

    if not repos:
        print("\n⚠️ 인덱싱된 저장소가 없습니다.\n")
        return

    # 첫 번째 저장소 정보 조회
    repo_id = repos[0]['repo_id']
    print(f"\nRepo ID: {repo_id}")

    info = manager.get_repository_info(repo_id)

    if info:
        print(f"\n📊 저장소 정보")
        print(f"경로: {info['repository_path']}")
        print(f"커밋 수: {info['commit_count']:,}")
        print(f"기여자 수: {info['author_count']}")
        print(f"날짜 범위:")
        print(f"  - 가장 오래된 커밋: {info['date_range']['oldest']}")
        print(f"  - 가장 최근 커밋: {info['date_range']['newest']}")
        print()


def example_6_health_check():
    """예제 6: 인덱스 상태 확인"""
    print("=" * 80)
    print("예제 6: 인덱스 상태 확인")
    print("=" * 80)

    _, search_client, index_client = initialize_clients()

    manager = IndexManager(
        search_client=search_client,
        index_client=index_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    health = manager.check_index_health()

    status_emoji = "✅" if health["status"] == "healthy" else "⚠️" if health["status"] == "degraded" else "❌"

    print(f"\n{status_emoji} 인덱스 상태: {health['status']}")
    print(f"인덱스 이름: {health.get('index_name', 'N/A')}")
    print(f"인덱스 존재: {'✓' if health.get('index_exists') else '✗'}")
    print(f"총 문서 수: {health.get('total_documents', 0):,}")
    print(f"검색 기능: {'정상' if health.get('search_works') else '오류'}")

    if "message" in health:
        print(f"메시지: {health['message']}")

    print()


def example_7_incremental_indexing():
    """예제 7: 증분 인덱싱"""
    print("=" * 80)
    print("예제 7: 증분 인덱싱")
    print("=" * 80)

    openai_client, search_client, index_client = initialize_clients()

    indexer = CommitIndexer(
        search_client=search_client,
        index_client=index_client,
        openai_client=openai_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    repo_path = "https://github.com/chainlit/chainlit"

    print(f"\n저장소: {repo_path}")
    print("증분 인덱싱 (이미 인덱싱된 커밋은 건너뛰기)")

    # 첫 번째 인덱싱 (최근 50개)
    print("\n1차 인덱싱 (최근 50개)...")
    count1 = indexer.index_repository(
        repo_path=repo_path,
        limit=50,
        skip_existing=True
    )
    print(f"✓ {count1}개 커밋 추가")

    # 두 번째 인덱싱 (최근 100개, 중복 제외)
    print("\n2차 인덱싱 (최근 100개, 중복 제외)...")
    count2 = indexer.index_repository(
        repo_path=repo_path,
        limit=100,
        skip_existing=True
    )
    print(f"✓ {count2}개 커밋 추가 (중복 제외)")
    print()


def example_8_multi_repository():
    """예제 8: 다중 저장소 인덱싱 및 통합 검색"""
    print("=" * 80)
    print("예제 8: 다중 저장소 인덱싱 및 통합 검색")
    print("=" * 80)

    openai_client, search_client, index_client = initialize_clients()

    indexer = CommitIndexer(
        search_client=search_client,
        index_client=index_client,
        openai_client=openai_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    # 여러 저장소 인덱싱
    repos = [
        "https://github.com/chainlit/chainlit",
        "https://github.com/langchain-ai/langchain",
    ]

    print("\n여러 저장소 인덱싱 중...\n")
    for repo in repos:
        print(f"📦 {repo}")
        count = indexer.index_repository(
            repo_path=repo,
            limit=50,
            skip_existing=True
        )
        print(f"   ✓ {count}개 커밋 추가\n")

    # 통합 검색
    query = "streaming response"
    print(f"통합 검색: '{query}'\n")

    results = search_commits(
        query=query,
        search_client=search_client,
        openai_client=openai_client,
        top=5
    )

    print(f"검색 결과: {len(results)}개 (모든 저장소)\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.get('repository', 'Unknown')}]")
        print(f"   {result['message'][:60]}...")
        print(f"   Author: {result['author']}, Score: {result['score']:.2f}")
        print()


def example_9_date_range_indexing():
    """예제 9: 날짜 범위 인덱싱"""
    print("=" * 80)
    print("예제 9: 날짜 범위 인덱싱")
    print("=" * 80)

    openai_client, search_client, index_client = initialize_clients()

    indexer = CommitIndexer(
        search_client=search_client,
        index_client=index_client,
        openai_client=openai_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    repo_path = "https://github.com/chainlit/chainlit"

    print(f"\n저장소: {repo_path}")
    print("2024년 커밋만 인덱싱\n")

    indexed_count = indexer.index_repository(
        repo_path=repo_path,
        since="2024-01-01",
        until="2024-12-31",
        skip_existing=True
    )

    print(f"✓ {indexed_count}개 커밋 인덱싱 완료 (2024년)\n")


def main():
    """메인 함수 - 모든 예제 실행"""
    print("\n")
    print("🚀 Azure AI Search Index 활용 예제")
    print("=" * 80)
    print()

    examples = [
        ("1", "기본 인덱싱", example_1_basic_indexing),
        ("2", "인덱스 통계 확인", example_2_index_statistics),
        ("3", "인덱싱된 저장소 목록", example_3_list_repositories),
        ("4", "커밋 검색", example_4_search_commits),
        ("5", "특정 저장소 정보 조회", example_5_repository_info),
        ("6", "인덱스 상태 확인", example_6_health_check),
        ("7", "증분 인덱싱", example_7_incremental_indexing),
        ("8", "다중 저장소 인덱싱 및 통합 검색", example_8_multi_repository),
        ("9", "날짜 범위 인덱싱", example_9_date_range_indexing),
    ]

    print("실행할 예제를 선택하세요:")
    for num, desc, _ in examples:
        print(f"  {num}. {desc}")
    print("  0. 모든 예제 실행")
    print("  q. 종료")
    print()

    choice = input("선택 (0-9 또는 q): ").strip().lower()

    if choice == 'q':
        print("\n종료합니다.\n")
        return

    if choice == '0':
        # 모든 예제 실행
        for num, desc, func in examples:
            try:
                func()
            except Exception as e:
                print(f"❌ 예제 {num} 실행 중 오류: {e}\n")
    else:
        # 특정 예제 실행
        for num, desc, func in examples:
            if choice == num:
                try:
                    func()
                except Exception as e:
                    print(f"❌ 오류 발생: {e}\n")
                return

        print(f"\n⚠️ 잘못된 선택: {choice}\n")


if __name__ == "__main__":
    main()

