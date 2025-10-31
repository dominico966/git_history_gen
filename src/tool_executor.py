"""
Tool execution helpers extracted from chat_app.py: resolve_repository_ambiguity and execute_tool.
This module imports the concrete tool implementations from project modules (src.tools, src.indexer, etc.)
and provides functions used by chat_app.
"""
import json
import logging
from typing import Dict, Any, Optional

import chainlit as cl
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from src.index_manager import IndexManager
from src.indexer import CommitIndexer
from src.online_reader import (
    OnlineRepoReader,
    read_file_from_commit,
    get_file_context,
    get_readme_content,
    get_commit_diff
)
from src.tools import (
    get_commit_summary,
    search_commits,
    analyze_contributors,
    find_frequent_bug_commits,
    get_commit_count
)

logger = logging.getLogger(__name__)

# limits (keep in sync with chat_app defaults)
import os
MAX_COMMIT_LIMIT = int(os.getenv("MAX_COMMIT_LIMIT", "1000"))
MAX_SEARCH_TOP = int(os.getenv("MAX_SEARCH_TOP", "50"))
MAX_CONTRIBUTOR_LIMIT = int(os.getenv("MAX_CONTRIBUTOR_LIMIT", "1000"))
DEFAULT_INDEX_LIMIT = int(os.getenv("DEFAULT_INDEX_LIMIT", "500"))
MAX_TOOL_RESULT_DISPLAY = 500
MAX_TOOL_RESULT_TO_LLM = 10000


async def resolve_repository_ambiguity(
    repo_hint: str,
    search_client: SearchClient,
    index_client: SearchIndexClient
) -> Optional[str]:
    index_manager = IndexManager(
        search_client=search_client,
        index_client=index_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    repos = index_manager.list_indexed_repositories()

    if not repos:
        return None

    matching_repos = [
        r for r in repos
        if repo_hint.lower() in r['repository_path'].lower()
    ]

    if len(matching_repos) == 0:
        return None
    elif len(matching_repos) == 1:
        return matching_repos[0]['repository_path']
    else:
        options_text = "🔍 여러 저장소가 발견되었습니다. 선택해주세요:\n\n"
        for i, repo in enumerate(matching_repos, 1):
            options_text += f"{i}. {repo['repository_path']} ({repo['commit_count']}개 커밋)\n"
        options_text += f"\n1-{len(matching_repos)} 사이의 숫자를 입력하세요:"

        res = await cl.AskUserMessage(
            content=options_text,
            timeout=60,
            raise_on_timeout=False
        ).send()

        if not res or not res.get("output"):
            logger.info("User timeout or cancelled repository selection")
            return None

        try:
            choice = int(res.get("output").strip())
            if 1 <= choice <= len(matching_repos):
                selected = matching_repos[choice - 1]['repository_path']
                await cl.Message(content=f"✅ 선택된 저장소: `{selected}`").send()
                return selected
            else:
                await cl.Message(content=f"❌ 유효하지 않은 번호입니다. 1-{len(matching_repos)} 사이의 숫자를 입력해주세요.").send()
                return None
        except ValueError:
            await cl.Message(content="❌ 숫자를 입력해주세요.").send()
            return None


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    openai_client: Any = None,
    search_client: Any = None,
    index_client: Any = None
) -> str:
    """Lightweight dispatcher for tools used by the chat app.
    This keeps the implementation small and avoids embedding the full original
    long code here. It calls into src.tools, IndexManager, and CommitIndexer as needed.
    """
    try:
        logger.info("Executing tool: %s args=%s", tool_name, arguments)

        # Helper to safely get arg
        def a(k, default=None):
            return arguments.get(k, default)

        # Simple mappings
        if tool_name == "get_commit_count":
            result = get_commit_count(repo_path=a("repo_path"), since=a("since"), until=a("until"))
            return json.dumps(result, ensure_ascii=False, indent=2)

        if tool_name == "get_commit_summary":
            return get_commit_summary(repo_path=a("repo_path"), llm_client=openai_client, limit=a("limit", 50))

        if tool_name == "search_commits":
            return json.dumps(
                search_commits(query=a("query"), search_client=search_client, openai_client=openai_client, top=a("top", 10), repo_path=a("repo_path")),
                ensure_ascii=False,
                indent=2
            )

        if tool_name == "analyze_contributors":
            return json.dumps(
                analyze_contributors(repo_path=a("repo_path"), criteria=a("criteria"), limit=a("limit"), since=a("since"), until=a("until")),
                ensure_ascii=False,
                indent=2
            )

        if tool_name in ("find_bug_commits", "find_frequent_bug_commits"):
            return json.dumps(
                find_frequent_bug_commits(repo_path=a("repo_path"), llm_client=openai_client, limit=a("limit", 200)),
                ensure_ascii=False,
                indent=2
            )

        if tool_name == "search_github_repo":
            reader = OnlineRepoReader()
            results = reader.search_github_repo(query=a("query"), max_results=a("max_results", 5))
            return json.dumps(results, ensure_ascii=False, indent=2)

        if tool_name == "read_file_from_commit":
            content = read_file_from_commit(repo_path=a("repo_path"), commit_sha=a("commit_sha"), file_path=a("file_path"))
            return content or ""

        if tool_name == "get_file_context":
            return json.dumps(get_file_context(repo_path=a("repo_path"), commit_sha=a("commit_sha"), file_path=a("file_path")), ensure_ascii=False, indent=2)

        if tool_name == "get_commit_diff":
            return json.dumps(get_commit_diff(repo_path=a("repo_path"), commit_sha=a("commit_sha"), max_files=a("max_files", 10)), ensure_ascii=False, indent=2)

        if tool_name == "get_readme":
            return get_readme_content(a("repo_path")) or ""

        if tool_name == "set_current_repository":
            repo_path = a("repo_path")
            cl.user_session.set("current_repository", repo_path)
            return f"현재 저장소를 '{repo_path}'로 설정했습니다."

        # Index / management operations via IndexManager / CommitIndexer
        if tool_name == "index_repository":
            try:
                indexer = CommitIndexer(
                    search_client=search_client,
                    index_client=index_client,
                    openai_client=openai_client,
                    index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
                )
                indexer.create_index_if_not_exists()
                indexed_count = indexer.index_repository(
                    repo_path=a("repo_path"),
                    limit=a("limit"),
                    since=a("since"),
                    until=a("until"),
                    skip_existing=a("skip_existing", True),
                    skip_offset=a("skip_offset", 0)
                )

                repo_path = a("repo_path")
                if indexed_count == 0:
                    return f"✅ '{repo_path}' 저장소의 모든 커밋이 이미 인덱싱되어 있습니다."
                else:
                    return f"✅ '{repo_path}' 저장소의 {indexed_count}개 커밋을 성공적으로 인덱싱했습니다."
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to index repository: {error_msg}")
                return f"❌ 인덱싱 실패: {error_msg}"

        if tool_name in ("get_index_statistics", "list_indexed_repositories", "get_repository_info", "delete_repository_commits", "check_index_health"):
            manager = IndexManager(search_client=search_client, index_client=index_client, index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits"))
            if tool_name == "get_index_statistics":
                return json.dumps(manager.get_index_statistics(), ensure_ascii=False, indent=2)
            if tool_name == "list_indexed_repositories":
                return json.dumps(manager.list_indexed_repositories(), ensure_ascii=False, indent=2)
            if tool_name == "get_repository_info":
                return json.dumps(manager.get_repository_info(a("repo_id")), ensure_ascii=False, indent=2)
            if tool_name == "delete_repository_commits":
                deleted = manager.delete_repository_commits(a("repo_id"))
                return str(deleted)
            if tool_name == "check_index_health":
                return json.dumps(manager.check_index_health(), ensure_ascii=False, indent=2)

        if tool_name == "search_commits_by_date":
            # a lightweight wrapper using search_client
            since = a("since")
            until = a("until")
            top = a("top", 50)
            filters = []
            if a("repo_path"):
                from src.indexer import normalize_repo_identifier
                repo_id = normalize_repo_identifier(a("repo_path"))
                filters.append(f"repo_id eq '{repo_id}'")
            if since:
                filters.append(f"date ge {since}T00:00:00Z")
            if until:
                filters.append(f"date le {until}T23:59:59Z")
            filter_expr = " and ".join(filters) if filters else None
            results = search_client.search(search_text="*", filter=filter_expr, select=["id","message","author","date","files_summary","repository_path"], order_by=["date desc"], top=min(top, MAX_SEARCH_TOP))
            commits = [
                {"commit_id": r.get("id"), "message": r.get("message"), "author": r.get("author"), "date": r.get("date"), "repository": r.get("repository_path")} for r in results
            ]
            return json.dumps(commits, ensure_ascii=False, indent=2)

        return f"알 수 없는 도구: {tool_name}"

    except Exception as e:
        logger.exception("Tool execution error")
        return f"도구 실행 중 오류 발생: {str(e)}"


def initialize_clients():
    """Initialize AzureOpenAI, SearchClient, SearchIndexClient and return them as a tuple.
    Imports are local to avoid hard dependency at module import time when not needed.
    """
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient as _SearchClient
    from azure.search.documents.indexes import SearchIndexClient as _SearchIndexClient
    from openai import AzureOpenAI as _AzureOpenAI

    openai_client = _AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    search_credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY"))

    search_client = _SearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        credential=search_credential
    )

    index_client = _SearchIndexClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        credential=search_credential
    )

    return openai_client, search_client, index_client


__all__ = ["resolve_repository_ambiguity", "execute_tool", "initialize_clients"]
