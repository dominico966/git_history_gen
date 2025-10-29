"""
Azure AI Search Index 관리 유틸리티
인덱스 상태 확인, 통계, 관리 기능 제공
"""

import logging
from typing import Dict, List, Optional, Any
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.exceptions import ResourceNotFoundError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IndexManager:
    """Azure AI Search 인덱스 관리 클래스"""

    def __init__(
        self,
        search_client: SearchClient,
        index_client: SearchIndexClient,
        index_name: str
    ):
        """
        Args:
            search_client: Azure AI Search 클라이언트
            index_client: Azure AI Search 인덱스 클라이언트
            index_name: 인덱스 이름
        """
        self.search_client = search_client
        self.index_client = index_client
        self.index_name = index_name

    def get_index_statistics(self) -> Dict[str, Any]:
        """
        인덱스 통계 정보를 반환합니다.

        Returns:
            Dict: 통계 정보
        """
        try:
            logger.info(f"Getting statistics for index: {self.index_name}")

            # 전체 문서 수 조회
            results = self.search_client.search(
                search_text="*",
                include_total_count=True,
                top=0
            )

            total_count = results.get_count()

            # 저장소별 통계
            repo_stats = self._get_repository_statistics()

            # 기여자별 통계
            author_stats = self._get_author_statistics()

            # 날짜 범위
            date_range = self._get_date_range()

            return {
                "total_commits": total_count,
                "repositories": len(repo_stats),
                "total_authors": len(author_stats),
                "date_range": date_range,
                "repository_details": repo_stats,
                "top_authors": sorted(
                    author_stats.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }

        except Exception as e:
            logger.error(f"Failed to get index statistics: {e}")
            return {
                "error": str(e),
                "total_commits": 0
            }

    def _get_repository_statistics(self) -> Dict[str, int]:
        """저장소별 커밋 수 조회"""
        try:
            results = self.search_client.search(
                search_text="*",
                facets=["repo_id,count:1000"],
                top=0
            )

            repo_facets = results.get_facets()
            if not repo_facets or "repo_id" not in repo_facets:
                return {}

            repo_stats = {}
            for facet in repo_facets["repo_id"]:
                repo_id = facet.get("value", "unknown")
                count = facet.get("count", 0)
                repo_stats[repo_id] = count

            return repo_stats

        except Exception as e:
            logger.warning(f"Failed to get repository statistics: {e}")
            return {}

    def _get_author_statistics(self) -> Dict[str, int]:
        """기여자별 커밋 수 조회"""
        try:
            results = self.search_client.search(
                search_text="*",
                facets=["author,count:1000"],
                top=0
            )

            author_facets = results.get_facets()
            if not author_facets or "author" not in author_facets:
                return {}

            author_stats = {}
            for facet in author_facets["author"]:
                author = facet.get("value", "unknown")
                count = facet.get("count", 0)
                author_stats[author] = count

            return author_stats

        except Exception as e:
            logger.warning(f"Failed to get author statistics: {e}")
            return {}

    def _get_date_range(self) -> Dict[str, Optional[str]]:
        """커밋 날짜 범위 조회"""
        try:
            # 가장 오래된 커밋
            oldest = self.search_client.search(
                search_text="*",
                order_by=["date asc"],
                select=["date"],
                top=1
            )

            # 가장 최근 커밋
            newest = self.search_client.search(
                search_text="*",
                order_by=["date desc"],
                select=["date"],
                top=1
            )

            oldest_date = None
            newest_date = None

            for result in oldest:
                oldest_date = result.get("date")
                break

            for result in newest:
                newest_date = result.get("date")
                break

            return {
                "oldest": str(oldest_date) if oldest_date else None,
                "newest": str(newest_date) if newest_date else None
            }

        except Exception as e:
            logger.warning(f"Failed to get date range: {e}")
            return {"oldest": None, "newest": None}

    def list_indexed_repositories(self) -> List[Dict[str, Any]]:
        """
        인덱싱된 저장소 목록을 반환합니다.

        Returns:
            List[Dict]: 저장소 정보 리스트
        """
        try:
            logger.info("Listing indexed repositories")

            results = self.search_client.search(
                search_text="*",
                select=["repo_id", "repository_path"],
                top=1000
            )

            # repo_id별로 그룹화
            repos = {}
            for result in results:
                repo_id = result.get("repo_id")
                repo_path = result.get("repository_path")

                if repo_id and repo_id not in repos:
                    repos[repo_id] = {
                        "repo_id": repo_id,
                        "repository_path": repo_path,
                        "commit_count": 0
                    }

                if repo_id:
                    repos[repo_id]["commit_count"] += 1

            return list(repos.values())

        except Exception as e:
            logger.error(f"Failed to list repositories: {e}")
            return []

    def delete_repository_commits(self, repo_id: str) -> int:
        """
        특정 저장소의 모든 커밋을 삭제합니다.

        Args:
            repo_id: 저장소 식별자

        Returns:
            int: 삭제된 문서 수
        """
        try:
            logger.info(f"Deleting commits for repository: {repo_id}")

            # 해당 저장소의 모든 커밋 ID 조회
            results = self.search_client.search(
                search_text="*",
                filter=f"repo_id eq '{repo_id}'",
                select=["id"],
                top=10000
            )

            commit_ids = [result["id"] for result in results]

            if not commit_ids:
                logger.info(f"No commits found for repo_id: {repo_id}")
                return 0

            # 배치 삭제
            batch_size = 1000
            deleted_count = 0

            for i in range(0, len(commit_ids), batch_size):
                batch = commit_ids[i:i + batch_size]
                documents_to_delete = [{"id": doc_id} for doc_id in batch]

                result = self.search_client.delete_documents(documents_to_delete)
                deleted_count += len(batch)

                logger.info(f"Deleted batch {i//batch_size + 1}: {len(batch)} documents")

            logger.info(f"✓ Deleted {deleted_count} commits for repo_id: {repo_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete repository commits: {e}")
            raise

    def clear_index(self) -> bool:
        """
        인덱스의 모든 문서를 삭제합니다 (주의: 인덱스 구조는 유지됨).

        Returns:
            bool: 성공 여부
        """
        try:
            logger.warning("Clearing all documents from index")

            # 모든 문서 ID 조회
            results = self.search_client.search(
                search_text="*",
                select=["id"],
                top=10000
            )

            all_ids = [result["id"] for result in results]

            if not all_ids:
                logger.info("Index is already empty")
                return True

            # 배치 삭제
            batch_size = 1000
            for i in range(0, len(all_ids), batch_size):
                batch = all_ids[i:i + batch_size]
                documents_to_delete = [{"id": doc_id} for doc_id in batch]
                self.search_client.delete_documents(documents_to_delete)

            logger.info(f"✓ Cleared {len(all_ids)} documents from index")
            return True

        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False

    def get_repository_info(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 저장소의 상세 정보를 조회합니다.

        Args:
            repo_id: 저장소 식별자

        Returns:
            Dict: 저장소 정보
        """
        try:
            logger.info(f"Getting info for repository: {repo_id}")

            # 커밋 수 조회
            results = self.search_client.search(
                search_text="*",
                filter=f"repo_id eq '{repo_id}'",
                include_total_count=True,
                top=0
            )

            commit_count = results.get_count()

            if commit_count == 0:
                logger.warning(f"No commits found for repo_id: {repo_id}")
                return None

            # 샘플 커밋 조회
            sample_results = self.search_client.search(
                search_text="*",
                filter=f"repo_id eq '{repo_id}'",
                select=["repository_path", "author", "date"],
                top=1
            )

            repo_path = None
            for result in sample_results:
                repo_path = result.get("repository_path")
                break

            # 기여자 조회
            author_results = self.search_client.search(
                search_text="*",
                filter=f"repo_id eq '{repo_id}'",
                facets=["author,count:100"],
                top=0
            )

            author_facets = author_results.get_facets()
            author_count = len(author_facets.get("author", [])) if author_facets else 0

            # 날짜 범위
            oldest = self.search_client.search(
                search_text="*",
                filter=f"repo_id eq '{repo_id}'",
                order_by=["date asc"],
                select=["date"],
                top=1
            )

            newest = self.search_client.search(
                search_text="*",
                filter=f"repo_id eq '{repo_id}'",
                order_by=["date desc"],
                select=["date"],
                top=1
            )

            oldest_date = None
            newest_date = None

            for result in oldest:
                oldest_date = result.get("date")
                break

            for result in newest:
                newest_date = result.get("date")
                break

            return {
                "repo_id": repo_id,
                "repository_path": repo_path,
                "commit_count": commit_count,
                "author_count": author_count,
                "date_range": {
                    "oldest": str(oldest_date) if oldest_date else None,
                    "newest": str(newest_date) if newest_date else None
                }
            }

        except Exception as e:
            logger.error(f"Failed to get repository info: {e}")
            return None

    def check_index_health(self) -> Dict[str, Any]:
        """
        인덱스 상태를 확인합니다.

        Returns:
            Dict: 상태 정보
        """
        try:
            logger.info("Checking index health")

            # 인덱스 존재 확인
            try:
                index = self.index_client.get_index(self.index_name)
                index_exists = True
            except ResourceNotFoundError:
                index_exists = False
                return {
                    "status": "error",
                    "message": f"Index '{self.index_name}' does not exist"
                }

            # 문서 수 확인
            results = self.search_client.search(
                search_text="*",
                include_total_count=True,
                top=0
            )

            total_docs = results.get_count()

            # 샘플 검색 테스트
            test_results = self.search_client.search(
                search_text="test",
                top=1
            )

            search_works = True
            try:
                for _ in test_results:
                    break
            except Exception as e:
                search_works = False
                logger.warning(f"Search test failed: {e}")

            status = "healthy" if index_exists and search_works else "degraded"

            return {
                "status": status,
                "index_exists": index_exists,
                "total_documents": total_docs,
                "search_works": search_works,
                "index_name": self.index_name
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


def format_index_statistics(stats: Dict[str, Any]) -> str:
    """
    통계 정보를 보기 좋게 포맷팅합니다.

    Args:
        stats: get_index_statistics() 반환값

    Returns:
        str: 포맷팅된 문자열
    """
    if "error" in stats:
        return f"❌ 오류: {stats['error']}"

    lines = [
        "📊 **인덱스 통계**",
        "",
        f"📦 총 커밋 수: {stats['total_commits']:,}",
        f"🗂️ 저장소 수: {stats['repositories']}",
        f"👥 기여자 수: {stats['total_authors']}",
        "",
        "📅 **날짜 범위**",
        f"  가장 오래된 커밋: {stats['date_range']['oldest'] or 'N/A'}",
        f"  가장 최근 커밋: {stats['date_range']['newest'] or 'N/A'}",
        "",
        "🏆 **Top 10 기여자**"
    ]

    for author, count in stats.get("top_authors", [])[:10]:
        lines.append(f"  - {author}: {count} commits")

    if stats.get("repository_details"):
        lines.append("")
        lines.append("📁 **저장소별 커밋 수**")
        for repo_id, count in sorted(
            stats["repository_details"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"  - {repo_id[:8]}...: {count} commits")

    return "\n".join(lines)

