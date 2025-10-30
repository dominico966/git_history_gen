"""
Azure AI Search 인덱싱 모듈
커밋 데이터를 Azure AI Search에 인덱싱하여 검색 가능하게 합니다.
"""

import logging
import hashlib
from typing import Optional, List, Set
from urllib.parse import urlparse
from pathlib import Path
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from openai import AzureOpenAI
from src.document_generator import DocumentGenerator
from src.embedding import embed_texts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_repo_identifier(repo_path: str) -> str:
    """
    저장소 경로 또는 URL을 정규화된 식별자로 변환합니다.

    Args:
        repo_path: Git 저장소 경로 또는 URL

    Returns:
        str: 정규화된 저장소 식별자 (해시값)
    """
    # URL인 경우
    if repo_path.startswith(('http://', 'https://', 'git://', 'ssh://')):
        parsed = urlparse(repo_path)
        # 스킴과 netloc, path를 사용하여 정규화
        # .git 확장자 제거
        path = parsed.path.rstrip('/').removesuffix('.git')
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}".lower()
    else:
        # 로컬 경로인 경우
        # 절대 경로로 변환하고 정규화
        abs_path = Path(repo_path).resolve()
        normalized = str(abs_path).lower()

    # SHA-256 해시로 변환 (짧은 버전 사용)
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    repo_id = hash_obj.hexdigest()[:16]  # 16자리로 축약

    logger.debug(f"Normalized '{repo_path}' -> '{normalized}' -> repo_id: {repo_id}")
    return repo_id


class CommitIndexer:
    """Git 커밋 데이터를 Azure AI Search에 인덱싱합니다."""

    def __init__(
        self,
        search_client: SearchClient,
        index_client: SearchIndexClient,
        openai_client: AzureOpenAI,
        index_name: str
    ):
        """
        Args:
            search_client: Azure AI Search 클라이언트
            index_client: Azure AI Search 인덱스 클라이언트
            openai_client: Azure OpenAI 클라이언트
            index_name: 인덱스 이름
        """
        self.search_client = search_client
        self.index_client = index_client
        self.openai_client = openai_client
        self.index_name = index_name

    def create_index_if_not_exists(self, vector_dimensions: int = 1536) -> None:
        """
        인덱스가 없으면 생성합니다.

        Args:
            vector_dimensions: 임베딩 벡터 차원 (기본값: 1536 for text-embedding-3-small)
        """
        try:
            # 인덱스가 이미 존재하는지 확인
            try:
                self.index_client.get_index(self.index_name)
                logger.info(f"Index '{self.index_name}' already exists")
                return
            except:
                pass

            # 인덱스 생성
            logger.info(f"Creating index '{self.index_name}'...")

            fields = [
                SimpleField(name="id", type="Edm.String", key=True, filterable=True),
                SimpleField(name="repo_id", type="Edm.String", filterable=True, facetable=True),
                SearchableField(name="repository_path", type="Edm.String", searchable=True),
                SearchableField(name="message", type="Edm.String", searchable=True),
                SimpleField(name="author", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="date", type="Edm.DateTimeOffset", filterable=True, sortable=True),
                SearchableField(name="files_summary", type="Edm.String", searchable=True),
                SimpleField(name="parent_ids", type="Collection(Edm.String)", filterable=True),
                SimpleField(name="files_changed_count", type="Edm.Int32", filterable=True, sortable=True),
                SimpleField(name="lines_added", type="Edm.Int32", filterable=True, sortable=True),
                SimpleField(name="lines_deleted", type="Edm.Int32", filterable=True, sortable=True),

                # 새로운 메타데이터 필드
                SearchableField(name="change_context_summary", type="Edm.String", searchable=True),
                SearchableField(name="impact_scope", type="Edm.String", searchable=True),
                SearchableField(name="modified_functions", type="Edm.String", searchable=True),
                SearchableField(name="modified_classes", type="Edm.String", searchable=True),
                SimpleField(name="code_complexity", type="Edm.String", filterable=True),
                SimpleField(name="relationship_type", type="Edm.String", filterable=True),
                SimpleField(name="same_author_as_prev", type="Edm.Boolean", filterable=True),

                SearchField(
                    name="content_vector",
                    type="Collection(Edm.Single)",
                    searchable=True,
                    vector_search_dimensions=vector_dimensions,
                    vector_search_profile_name="default-vector-profile"
                ),
            ]

            # Vector search configuration
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="default-vector-profile",
                        algorithm_configuration_name="default-hnsw"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(name="default-hnsw")
                ]
            )

            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search
            )

            self.index_client.create_index(index)
            logger.info(f"✓ Index '{self.index_name}' created successfully")

        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise

    def _get_existing_ids_for_candidates(self, repo_id: str, candidate_ids: List[str], chunk_size: int = 800) -> Set[str]:
        """
        주어진 후보 커밋 id 집합에 대해, 인덱스에 이미 존재하는 id만 배치로 조회하여 반환합니다.
        search.in 함수를 사용해 OData 필터로 한 번에 여러 id를 확인합니다.
        """
        existing: Set[str] = set()
        if not candidate_ids:
            return existing
        try:
            # 안전하게 청크로 나누어 처리 (필드 길이/쿼리 길이 제한 대비)
            for i in range(0, len(candidate_ids), chunk_size):
                chunk = candidate_ids[i:i + chunk_size]
                ids_joined = ",".join(chunk)
                filter_expr = f"repo_id eq '{repo_id}' and search.in(id, '{ids_joined}', ',')"
                results = self.search_client.search(
                    search_text="*",
                    filter=filter_expr,
                    select=["id"],
                    top=len(chunk)
                )
                for r in results:
                    try:
                        existing.add(r["id"])  # 최소 필드만 접근
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Failed to batch-check existing ids: {e}")
        return existing

    def index_repository(
        self,
        repo_path: str,
        limit: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        skip_existing: bool = True,
        skip_offset: int = 0,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Git 저장소의 커밋 데이터를 인덱싱합니다.

        Args:
            repo_path: Git 저장소 경로 또는 URL
            limit: 인덱싱할 최대 커밋 수 (기본값: None = 전체)
            since: 시작 날짜 (ISO 8601 형식, 예: '2024-01-01')
            until: 종료 날짜 (ISO 8601 형식, 예: '2024-12-31')
            skip_existing: 이미 인덱싱된 커밋 건너뛰기 (증분 인덱싱, 기본값: True)
            skip_offset: HEAD부터 건너뛸 커밋 수 (과거 커밋 추가 시 사용, 기본값: 0)
            progress_callback: 진행 상황 콜백 함수 (current, total, message)

        Returns:
            int: 인덱싱된 문서 수
        """
        try:
            # 저장소 식별자 생성
            repo_id = normalize_repo_identifier(repo_path)

            # 📊 인덱싱 조건 요약 로그
            logger.info("=" * 80)
            logger.info("📊 INDEXING REQUEST SUMMARY")
            logger.info(f"  📁 Repository: {repo_path}")
            logger.info(f"  🔑 Repo ID: {repo_id}")
            logger.info(f"  📈 Limit: {limit if limit else 'ALL commits'}")
            logger.info(f"  📅 Date Range: {since or 'start'} ~ {until or 'end'}")
            logger.info(f"  🔄 Skip Existing: {skip_existing}")
            logger.info(f"  ⏭️  Skip Offset: {skip_offset}")
            logger.info("=" * 80)

            # 이미 인덱싱된 커밋 ID 확인 전략:
            # 1) 전체 스캔 대신, 후보 커밋 목록을 먼저 수집한 뒤 해당 id들만 배치 조회(search.in)로 존재 여부 확인
            # 2) 그 결과를 기반으로 새 커밋만 필터링 (정확/저비용)

            # skip_offset이 크면 미리 충분한 depth로 fetch (원격 저장소만)
            if skip_offset > 0 and repo_path.startswith(('http://', 'https://', 'git@', 'ssh://')):
                required_depth = skip_offset + (limit if limit else 100)
                logger.info(f"Skip offset {skip_offset} detected, pre-fetching with depth={required_depth}")

                from src.repo_cache import RepoCloneCache
                cache = RepoCloneCache()
                cache.get_or_clone(repo_path, depth=required_depth)

            # 커밋 데이터 추출
            generator = DocumentGenerator(repo_path)
            try:
                commits = generator.get_commits(limit=limit, since=since, until=until, skip=skip_offset)
            finally:
                generator.close()  # 파일 핸들 해제

            if not commits:
                if skip_offset > 0:
                    logger.warning(f"No commits found with skip_offset={skip_offset}. Shallow clone may not have enough commits.")
                    logger.warning(f"Try with smaller skip_offset or ensure repository is fully fetched.")
                else:
                    logger.warning("No commits found")
                return 0

            # 증분 스킵: 후보 집합에 대해서만 존재 여부 확인
            if skip_existing:
                candidate_ids = [c['id'] for c in commits]
                existing_commit_ids = self._get_existing_ids_for_candidates(repo_id, candidate_ids)
                original_count = len(commits)
                commits = [c for c in commits if c['id'] not in existing_commit_ids]
                skipped = original_count - len(commits)
                if skipped > 0:
                    logger.info(f"Skipped {skipped} already indexed commits")

            if not commits:
                logger.info("All commits are already indexed")
                return 0

            logger.info(f"Found {len(commits)} commits to index")

            # 문서 준비
            documents = []
            texts_to_embed = []

            total_commits = len(commits)

            for idx, commit in enumerate(commits):
                # 진행 상황 콜백
                if progress_callback:
                    try:
                        progress_callback(idx, total_commits, "문서 준비 중")
                    except:
                        pass

                # 임베딩할 텍스트 생성 (향상된 문맥 포함)
                files_info = [f"{f['file']} ({f['change_type']})" for f in commit['files']]

                # 변경 문맥 포함
                change_context = commit.get('change_context', {})
                function_analysis = commit.get('function_analysis', {})

                # 함수 변경 정보 추가
                func_changes = []
                if function_analysis.get('modified_functions'):
                    func_changes.append("Modified: " + ", ".join(
                        [f"{f['name']} in {f['file']}" for f in function_analysis['modified_functions'][:3]]
                    ))
                if function_analysis.get('added_functions'):
                    func_changes.append("Added: " + ", ".join(
                        [f['name'] for f in function_analysis['added_functions'][:3]]
                    ))

                text_content = f"""Commit: {commit['message']}
Author: {commit['author']}
Files: {', '.join(files_info)}
Context: {change_context.get('summary', '')}
Functions: {'; '.join(func_changes) if func_changes else 'No function changes'}"""

                texts_to_embed.append(text_content)

                # 통계 계산
                lines_added = sum(f.get('lines_added', 0) for f in commit['files'])
                lines_deleted = sum(f.get('lines_deleted', 0) for f in commit['files'])

                # 기본 문서 데이터
                doc = {
                    "id": commit['id'],
                    "repo_id": repo_id,
                    "repository_path": repo_path,
                    "message": commit['message'],
                    "author": commit['author'],
                    "date": commit['date'],
                    "files_summary": ', '.join(files_info),
                    "parent_ids": commit.get('parents', []),
                    "files_changed_count": len(commit['files']),
                    "lines_added": lines_added,
                    "lines_deleted": lines_deleted,
                }

                # 새로운 메타데이터 추가
                doc["change_context_summary"] = change_context.get('summary', '')
                doc["impact_scope"] = '; '.join(change_context.get('impact_scope', [])[:5])

                # 함수 분석 메타데이터
                modified_funcs = [f"{f['name']} ({f['file']})"
                                 for f in function_analysis.get('modified_functions', [])[:10]]
                doc["modified_functions"] = ', '.join(modified_funcs) if modified_funcs else ''

                modified_classes = [f"{c['name']} ({c['file']})"
                                   for c in function_analysis.get('modified_classes', [])[:10]]
                doc["modified_classes"] = ', '.join(modified_classes) if modified_classes else ''

                doc["code_complexity"] = function_analysis.get('code_complexity_hint', 'unknown')

                # 커밋 관계 메타데이터
                relation = commit.get('relation_to_previous')
                if relation:
                    doc["relationship_type"] = relation.get('relationship_type', 'sequential')
                    doc["same_author_as_prev"] = relation.get('same_author', False)
                else:
                    doc["relationship_type"] = 'initial'
                    doc["same_author_as_prev"] = False

                documents.append(doc)

            # 임베딩 생성
            if progress_callback:
                try:
                    progress_callback(total_commits, total_commits, "임베딩 생성 중")
                except:
                    pass

            logger.info("Generating embeddings...")
            embeddings = embed_texts(texts_to_embed, self.openai_client)

            # 임베딩을 문서에 추가
            for doc, embedding in zip(documents, embeddings):
                doc["content_vector"] = embedding

            # 업로드
            if progress_callback:
                try:
                    progress_callback(total_commits, total_commits, "업로드 중")
                except:
                    pass

            logger.info(f"Uploading {len(documents)} documents to Azure AI Search...")
            result = self.search_client.upload_documents(documents=documents)

            success_count = sum(1 for r in result if r.succeeded)

            logger.info("=" * 80)
            logger.info(f"✅ INDEXING COMPLETED")
            logger.info(f"  📊 Successfully indexed: {success_count}/{len(documents)} documents")
            logger.info(f"  📁 Repository: {repo_path}")
            logger.info(f"  🔑 Repo ID: {repo_id}")
            logger.info("=" * 80)

            return success_count

        except Exception as e:
            logger.error(f"Failed to index repository: {e}")
            raise

    def delete_index(self) -> None:
        """인덱스를 삭제합니다."""
        try:
            logger.info(f"Deleting index '{self.index_name}'...")
            self.index_client.delete_index(self.index_name)
            logger.info(f"✓ Index '{self.index_name}' deleted")
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            raise
