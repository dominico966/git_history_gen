"""
도구 함수들 - Streamlit 앱에서 사용할 다양한 기능 제공
"""

import os
from src.document_generator import DocumentGenerator
from typing import List, Dict, Optional, Any
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from src.embedding import embed_texts
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_repo_identifier(repo_path: str) -> str:
    """
    저장소 경로 또는 URL을 정규화된 식별자로 변환합니다.
    (indexer.py의 함수와 동일한 로직)
    """
    import hashlib
    from urllib.parse import urlparse
    from pathlib import Path

    # git@ 형식의 SSH URL 처리 (예: git@github.com:user/repo.git)
    if repo_path.startswith('git@'):
        # git@github.com:user/repo.git -> github.com/user/repo 형식으로 변환
        parts = repo_path.replace('git@', '').replace(':', '/')
        normalized = parts.rstrip('/').removesuffix('.git').lower()
    # 일반 URL인 경우 (http://, https://, git://, ssh://)
    elif repo_path.startswith(('http://', 'https://', 'git://', 'ssh://')):
        parsed = urlparse(repo_path)
        path = parsed.path.rstrip('/').removesuffix('.git')
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}".lower()
    else:
        # 로컬 경로인 경우
        try:
            abs_path = Path(repo_path).resolve()
            normalized = str(abs_path).lower()
        except Exception as e:
            # 경로 변환 실패 시 원본 사용
            logger.warning(f"Failed to resolve path '{repo_path}': {e}, using original")
            normalized = repo_path.lower()

    # SHA-256 해시로 변환
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    repo_id = hash_obj.hexdigest()[:16]

    return repo_id


def get_commit_count(
    repo_path: str,
    since: Optional[str] = None,
    until: Optional[str] = None
) -> Dict[str, Any]:
    """
    저장소의 총 커밋 개수를 확인합니다.
    캐시된 저장소에서 정확한 개수를 조회합니다.

    Args:
        repo_path: Git 저장소 경로 또는 URL
        since: 시작 날짜 (ISO 8601 형식, 예: '2024-01-01')
        until: 종료 날짜 (ISO 8601 형식, 예: '2024-12-31')

    Returns:
        Dict: 커밋 개수 정보
    """
    try:
        logger.info(f"Counting commits for {repo_path} (since={since}, until={until})")

        # 원격 저장소인 경우
        if repo_path.startswith(('http://', 'https://', 'git@')):
            # 캐시된 클론 사용 (정확한 개수)
            logger.info("Using cached repository for accurate commit count...")
            from src.repo_cache import RepoCloneCache

            cache = RepoCloneCache()

            # 날짜 필터가 있으면 충분한 depth 필요
            if since or until:
                # 날짜 필터가 있으면 더 깊게 fetch
                cached_path = cache.get_or_clone(repo_path, depth=1000)
            else:
                # 날짜 필터 없으면 shallow clone으로 충분
                cached_path = cache.get_or_clone(repo_path)

            # 캐시된 저장소에서 커밋 개수 조회
            import git
            repo = git.Repo(cached_path)

            args = ['--count', 'HEAD']
            if since:
                args.append(f'--since={since}')
            if until:
                args.append(f'--until={until}')

            count = int(repo.git.rev_list(*args))
            repo.close()

            period_text = ""
            if since and until:
                period_text = f" ({since} ~ {until})"
            elif since:
                period_text = f" ({since} 이후)"
            elif until:
                period_text = f" ({until} 이전)"

            logger.info(f"✓ Cached repo: {count:,} commits{period_text}")

            # 0개 커밋인 경우 명확한 메시지 생성
            if count == 0:
                if since or until:
                    message = f"⚠️ 지정한 기간{period_text}에는 커밋이 없습니다. 날짜 범위를 조정해보세요."
                else:
                    message = "⚠️ 이 저장소에는 커밋이 없습니다."

                return {
                    "repo_path": repo_path,
                    "commit_count": 0,
                    "has_commits": False,
                    "since": since,
                    "until": until,
                    "method": "cached_clone",
                    "message": message
                }

            return {
                "repo_path": repo_path,
                "commit_count": count,
                "has_commits": True,
                "since": since,
                "until": until,
                "method": "cached_clone",
                "message": f"총 {count:,}개 커밋{period_text}"
            }

        # 로컬 저장소인 경우 - 기존 방식 유지
        generator = DocumentGenerator(repo_path)
        try:
            repo = generator.repo
            args = ['--count', 'HEAD']

            if since:
                args.append(f'--since={since}')
            if until:
                args.append(f'--until={until}')

            commit_count = int(repo.git.rev_list(*args))

            period_text = ""
            if since and until:
                period_text = f" ({since} ~ {until})"
            elif since:
                period_text = f" ({since} 이후)"
            elif until:
                period_text = f" ({until} 이전)"

            # 0개 커밋인 경우 명확한 메시지 생성
            if commit_count == 0:
                if since or until:
                    message = f"⚠️ 지정한 기간{period_text}에는 커밋이 없습니다. 날짜 범위를 조정해보세요."
                else:
                    message = "⚠️ 이 저장소에는 커밋이 없습니다."

                return {
                    "repo_path": repo_path,
                    "commit_count": 0,
                    "has_commits": False,
                    "since": since,
                    "until": until,
                    "method": "local",
                    "message": message
                }

            return {
                "repo_path": repo_path,
                "commit_count": commit_count,
                "has_commits": True,
                "since": since,
                "until": until,
                "method": "local",
                "message": f"총 {commit_count:,}개 커밋{period_text}"
            }
        finally:
            generator.close()

    except Exception as e:
        logger.error(f"Error counting commits: {e}")
        return {
            "repo_path": repo_path,
            "commit_count": 0,
            "has_commits": False,
            "error": str(e),
            "message": f"커밋 개수 확인 실패: {str(e)}"
        }



def get_commit_summary(
    repo_path: str,
    llm_client: AzureOpenAI,
    limit: int = 50
) -> str:
    """
    Git 저장소의 최근 커밋들을 요약합니다.

    Args:
        repo_path: Git 저장소 경로
        llm_client: Azure OpenAI 클라이언트
        limit: 분석할 커밋 수

    Returns:
        str: LLM이 생성한 커밋 요약
    """
    try:
        logger.info(f"Generating summary for {repo_path} (last {limit} commits)")

        generator = DocumentGenerator(repo_path)
        try:
            commits = generator.get_commits(limit=limit)
        finally:
            generator.close()  # 파일 핸들 해제

        if not commits:
            return "No commits found in the repository."

        # 커밋 정보를 구조화된 형태로 정리
        commit_summary = []
        for commit in commits[:10]:  # 최근 10개만 상세 표시
            files_changed = len(commit['files'])
            lines_added = sum(f.get('lines_added', 0) for f in commit['files'])
            lines_deleted = sum(f.get('lines_deleted', 0) for f in commit['files'])

            commit_summary.append(
                f"- [{commit['date'][:10]}] {commit['author']}: {commit['message'][:100]}\n"
                f"  Files: {files_changed}, +{lines_added}/-{lines_deleted}"
            )

        # 통계 정보
        total_authors = len(set(c['author'] for c in commits))
        total_files = sum(len(c['files']) for c in commits)

        # LLM에게 요약 요청
        prompt = f"""다음은 Git 저장소의 최근 {len(commits)}개 커밋 정보입니다.

최근 10개 커밋 상세:
{chr(10).join(commit_summary)}

전체 통계:
- 총 커밋 수: {len(commits)}
- 기여자 수: {total_authors}
- 변경된 파일 수: {total_files}

다음 관점에서 분석하여 요약해주세요:
1. 최근 변경사항의 주요 특징
2. 가장 활발하게 변경된 영역
3. 주요 기여자 활동
4. 주목할 만한 패턴이나 트렌드

간결하고 명확하게 한국어로 작성해주세요."""

        from openai.types.chat import ChatCompletionMessageParam

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": "당신은 Git 커밋 히스토리를 분석하는 전문가입니다."},
            {"role": "user", "content": prompt}
        ]

        response = llm_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4.1-mini"),
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error generating commit summary: {e}")
        return f"Error generating summary: {str(e)}"


def search_commits(
    query: str,
    search_client: SearchClient,
    openai_client: AzureOpenAI,
    top: int = 10,
    repo_path: Optional[str] = None
) -> List[Dict]:
    """
    자연어 쿼리로 커밋을 검색합니다 (벡터 + 하이브리드 검색).

    Args:
        query: 검색 쿼리
        search_client: Azure AI Search 클라이언트
        openai_client: Azure OpenAI 클라이언트
        top: 반환할 최대 결과 수
        repo_path: 특정 저장소만 검색 (선택적)

    Returns:
        List[Dict]: 검색 결과 리스트
    """
    try:
        # 🔍 검색 조건 요약 로그
        logger.info("=" * 80)
        logger.info("🔍 SEARCH REQUEST SUMMARY")
        logger.info(f"  📝 Query: '{query}'")
        logger.info(f"  📊 Top Results: {top}")
        logger.info(f"  📁 Repository Filter: {repo_path if repo_path else 'ALL repositories'}")
        if repo_path:
            repo_id = normalize_repo_identifier(repo_path)
            logger.info(f"  🔑 Repo ID: {repo_id}")
        logger.info("=" * 80)

        # 쿼리 임베딩
        query_embeddings = embed_texts([query], openai_client)

        if not query_embeddings or not query_embeddings[0]:
            logger.error("Failed to generate query embedding")
            return []

        # 벡터 검색 쿼리 생성
        vector_query = VectorizedQuery(
            vector=query_embeddings[0],
            k_nearest_neighbors=top,
            fields="content_vector"
        )

        # 저장소 필터 추가 (repo_path가 제공된 경우)
        filter_expr = None
        if repo_path:
            repo_id = normalize_repo_identifier(repo_path)
            filter_expr = f"repo_id eq '{repo_id}'"
            logger.info(f"📌 Applying filter: {filter_expr}")

        # 하이브리드 검색 (텍스트 + 벡터)
        logger.info(f"🔎 Executing hybrid search (text + vector)...")
        results = search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=filter_expr,
            select=[
                "id", "message", "author", "date", "files_summary",
                "lines_added", "lines_deleted",
                "repo_id", "repository_path",
                "change_context_summary", "impact_scope",
                "modified_functions", "modified_classes",
                "code_complexity", "relationship_type"
            ],
            top=top
        )

        search_results = []
        for result in results:
            search_results.append({
                "commit_id": result.get("id", ""),
                "message": result.get("message", ""),
                "author": result.get("author", ""),
                "date": result.get("date", ""),
                "files": result.get("files_summary", ""),
                "changes": f"+{result.get('lines_added', 0)}/-{result.get('lines_deleted', 0)}",
                "score": result.get("@search.score", 0),
                "repo_id": result.get("repo_id", ""),
                "repository": result.get("repository_path", ""),
                # 새로운 메타데이터
                "context": result.get("change_context_summary", ""),
                "impact": result.get("impact_scope", ""),
                "functions": result.get("modified_functions", ""),
                "classes": result.get("modified_classes", ""),
                "complexity": result.get("code_complexity", "unknown"),
                "relation": result.get("relationship_type", "sequential")
            })

        logger.info("=" * 80)
        logger.info(f"✅ SEARCH COMPLETED: Found {len(search_results)} results")
        if search_results:
            logger.info(f"  📌 Top result: [{search_results[0]['commit_id'][:8]}] {search_results[0]['message'][:60]}...")
            logger.info(f"  🎯 Score range: {search_results[0]['score']:.4f} ~ {search_results[-1]['score']:.4f}")
        logger.info("=" * 80)
        return search_results

    except Exception as e:
        logger.error(f"Error searching commits: {e}")
        return []


def analyze_contributors(
    repo_path: str,
    criteria: Optional[str] = None,
    limit: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None
) -> Dict:
    """
    기여자별 활동을 분석합니다.

    Args:
        repo_path: Git 저장소 경로
        criteria: 평가 기준 (None이면 기본값 사용)
        limit: 분석할 커밋 수
        since: 시작 날짜 (ISO 8601 형식, 예: '2024-01-01')
        until: 종료 날짜 (ISO 8601 형식, 예: '2024-12-31')

    Returns:
        Dict: 기여자별 통계
    """
    try:
        logger.info(f"Analyzing contributors for {repo_path} (since: {since}, until: {until})")

        generator = DocumentGenerator(repo_path)
        try:
            commits = generator.get_commits(
                limit=limit if limit else 1000,
                since=since,
                until=until
            )
        finally:
            generator.close()  # 파일 핸들 해제

        if not commits:
            return {"error": "No commits found"}

        # 기여자별 통계 수집
        contributor_stats = defaultdict(lambda: {
            "commit_count": 0,
            "files_changed": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "recent_commits": []
        })

        for commit in commits:
            author = commit['author']
            stats = contributor_stats[author]

            stats["commit_count"] += 1
            stats["files_changed"] += len(commit['files'])
            stats["lines_added"] += sum(f.get('lines_added', 0) for f in commit['files'])
            stats["lines_deleted"] += sum(f.get('lines_deleted', 0) for f in commit['files'])

            if len(stats["recent_commits"]) < 5:
                stats["recent_commits"].append({
                    "date": commit['date'][:10],
                    "message": commit['message'][:100]
                })

        # 기본 평가 기준 적용 (없으면)
        if not criteria:
            criteria = "커밋 수, 변경 라인 수"

        # 결과를 정렬된 리스트로 변환
        result = {
            "total_contributors": len(contributor_stats),
            "total_commits": len(commits),
            "evaluation_criteria": criteria,
            "contributors": []
        }

        # 커밋 수로 정렬
        for author, stats in sorted(
            contributor_stats.items(),
            key=lambda x: x[1]["commit_count"],
            reverse=True
        ):
            total_lines = stats["lines_added"] + stats["lines_deleted"]
            result["contributors"].append({
                "name": author,
                "commits": stats["commit_count"],
                "files_changed": stats["files_changed"],
                "lines_added": stats["lines_added"],
                "lines_deleted": stats["lines_deleted"],
                "total_lines_changed": total_lines,
                "recent_commits": stats["recent_commits"]
            })

        logger.info(f"✓ Analyzed {len(result['contributors'])} contributors")
        return result

    except Exception as e:
        logger.error(f"Error analyzing contributors: {e}")
        return {"error": str(e)}


def find_frequent_bug_commits(
    repo_path: str,
    llm_client: AzureOpenAI,
    limit: int = 200
) -> List[Dict]:
    """
    버그 수정 커밋을 찾습니다 (커밋 메시지 기반).

    Args:
        repo_path: Git 저장소 경로
        llm_client: Azure OpenAI 클라이언트 (추가 분석용)
        limit: 분석할 커밋 수

    Returns:
        List[Dict]: 버그 관련 커밋 리스트
    """
    try:
        logger.info(f"Finding bug-related commits in {repo_path}")

        generator = DocumentGenerator(repo_path)
        try:
            commits = generator.get_commits(limit=limit)
        finally:
            generator.close()  # 파일 핸들 해제

        # 버그 관련 키워드
        bug_keywords = ['fix', 'bug', 'issue', 'patch', 'hotfix', 'bugfix', '수정', '버그', '오류']

        bug_commits = []
        for commit in commits:
            message_lower = commit['message'].lower()
            if any(keyword in message_lower for keyword in bug_keywords):
                bug_commits.append({
                    "id": commit['id'][:8],
                    "message": commit['message'],
                    "author": commit['author'],
                    "date": commit['date'][:10],
                    "files_changed": len(commit['files']),
                })

        logger.info(f"✓ Found {len(bug_commits)} bug-related commits")
        return bug_commits

    except Exception as e:
        logger.error(f"Error finding bug commits: {e}")
        return []

