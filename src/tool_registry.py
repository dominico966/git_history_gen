"""
Tool registry: provides a `tool` decorator, registers pydantic-based parameter models
and exposes `AVAILABLE_TOOLS` for use by the chat app.
This module is intentionally small and import-safe.
"""
from typing import Dict, Any

# Optional pydantic import
try:
    from pydantic import BaseModel
except Exception:
    BaseModel = None

_tool_registry: Dict[str, Any] = {}


def tool(name: str, description: str, parameters: Any):
    """Decorator to register a tool. Accepts either a dict schema or a pydantic model class."""
    def decorator(func):
        if isinstance(parameters, dict):
            params_schema = parameters
        else:
            if BaseModel and isinstance(parameters, type) and issubclass(parameters, BaseModel):
                # pydantic v2 preferred
                if hasattr(parameters, "model_json_schema") and callable(getattr(parameters, "model_json_schema")):
                    try:
                        params_schema = parameters.model_json_schema()
                    except Exception:
                        params_schema = {}
                else:
                    schema_func = getattr(parameters, "schema", None)
                    if callable(schema_func):
                        try:
                            params_schema = schema_func()
                        except Exception:
                            params_schema = {}
                    else:
                        params_schema = {}
            else:
                params_schema = {}

        func.tool_metadata = {
            "name": name,
            "description": description,
            "parameters": params_schema,
        }
        _tool_registry[name] = func
        return func

    return decorator


def generate_available_tools():
    tools = []
    for name, func in _tool_registry.items():
        metadata = getattr(func, "tool_metadata", None)
        if not metadata:
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": metadata["name"],
                "description": metadata["description"],
                "parameters": metadata.get("parameters", {}),
            }
        })
    return tools


# --- Register pydantic models and stubs (if pydantic available) ---
if BaseModel:
    from typing import Optional

    class GetCommitCountParams(BaseModel):
        repo_path: str
        since: Optional[str] = None
        until: Optional[str] = None

    class GetCommitSummaryParams(BaseModel):
        repo_path: str
        limit: Optional[int] = 50

    class SearchCommitsParams(BaseModel):
        query: str
        top: Optional[int] = 10
        repo_path: Optional[str] = None

    class AnalyzeContributorsParams(BaseModel):
        repo_path: str
        criteria: Optional[str] = None
        limit: Optional[int] = None
        since: Optional[str] = None
        until: Optional[str] = None

    class FindBugCommitsParams(BaseModel):
        repo_path: str
        limit: Optional[int] = 200

    class SearchGithubRepoParams(BaseModel):
        query: str
        max_results: Optional[int] = 5

    class ReadFileFromCommitParams(BaseModel):
        repo_path: str
        commit_sha: str
        file_path: str

    class GetFileContextParams(BaseModel):
        repo_path: str
        commit_sha: str
        file_path: str

    class GetCommitDiffParams(BaseModel):
        repo_path: str
        commit_sha: str
        max_files: Optional[int] = 10

    class GetReadmeParams(BaseModel):
        repo_path: str

    class SetCurrentRepositoryParams(BaseModel):
        repo_path: str

    class IndexRepositoryParams(BaseModel):
        repo_path: str
        limit: Optional[int] = None
        since: Optional[str] = None
        until: Optional[str] = None
        skip_existing: Optional[bool] = True
        skip_offset: Optional[int] = 0

    class EmptyParams(BaseModel):
        pass

    class GetRepositoryInfoParams(BaseModel):
        repo_id: str

    class DeleteRepositoryCommitsParams(BaseModel):
        repo_id: str

    class SearchCommitsByDateParams(BaseModel):
        since: Optional[str] = None
        until: Optional[str] = None
        repo_path: Optional[str] = None
        top: Optional[int] = 50

    # stubs (tools are executed by tool_executor.execute_tool)
    @tool(name="get_commit_count", description="저장소의 총 커밋 개수를 빠르게 확인합니다.", parameters=GetCommitCountParams)
    def _get_commit_count_stub(**kwargs):
        return None

    @tool(name="get_commit_summary", description="최근 커밋 요약", parameters=GetCommitSummaryParams)
    def _get_commit_summary_stub(**kwargs):
        return None

    @tool(name="search_commits", description="자연어 쿼리로 커밋을 검색합니다.", parameters=SearchCommitsParams)
    def _search_commits_stub(**kwargs):
        return None

    @tool(name="analyze_contributors", description="기여자별 활동을 분석합니다.", parameters=AnalyzeContributorsParams)
    def _analyze_contributors_stub(**kwargs):
        return None

    @tool(name="find_bug_commits", description="버그 수정 커밋을 찾습니다.", parameters=FindBugCommitsParams)
    def _find_bug_commits_stub(**kwargs):
        return None

    @tool(name="search_github_repo", description="GitHub 저장소 검색", parameters=SearchGithubRepoParams)
    def _search_github_repo_stub(**kwargs):
        return None

    @tool(name="read_file_from_commit", description="커밋의 파일 내용을 읽습니다.", parameters=ReadFileFromCommitParams)
    def _read_file_from_commit_stub(**kwargs):
        return None

    @tool(name="get_file_context", description="파일의 변경 컨텍스트를 가져옵니다.", parameters=GetFileContextParams)
    def _get_file_context_stub(**kwargs):
        return None

    @tool(name="get_commit_diff", description="커밋의 diff를 가져옵니다.", parameters=GetCommitDiffParams)
    def _get_commit_diff_stub(**kwargs):
        return None

    @tool(name="get_readme", description="저장소 README 가져오기", parameters=GetReadmeParams)
    def _get_readme_stub(**kwargs):
        return None

    @tool(name="set_current_repository", description="현재 저장소 설정", parameters=SetCurrentRepositoryParams)
    def _set_current_repository_stub(**kwargs):
        return None

    @tool(name="index_repository", description="저장소 인덱싱", parameters=IndexRepositoryParams)
    def _index_repository_stub(**kwargs):
        return None

    @tool(name="get_index_statistics", description="인덱스 통계 조회", parameters=EmptyParams)
    def _get_index_statistics_stub(**kwargs):
        return None

    @tool(name="list_indexed_repositories", description="인덱싱된 저장소 목록", parameters=EmptyParams)
    def _list_indexed_repositories_stub(**kwargs):
        return None

    @tool(name="get_repository_info", description="저장소 정보 조회", parameters=GetRepositoryInfoParams)
    def _get_repository_info_stub(**kwargs):
        return None

    @tool(name="delete_repository_commits", description="저장소 커밋 삭제", parameters=DeleteRepositoryCommitsParams)
    def _delete_repository_commits_stub(**kwargs):
        return None

    @tool(name="check_index_health", description="인덱스 상태 확인", parameters=EmptyParams)
    def _check_index_health_stub(**kwargs):
        return None

    @tool(name="search_commits_by_date", description="날짜 범위로 커밋 조회", parameters=SearchCommitsByDateParams)
    def _search_commits_by_date_stub(**kwargs):
        return None

else:
    # fallback: register one minimal dict-based tool to ensure registry isn't empty
    def _fallback_get_commit_count(**kwargs):
        return None

    tool(
        name="get_commit_count",
        description="저장소의 총 커밋 개수를 빠르게 확인합니다.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "since": {"type": "string"},
                "until": {"type": "string"}
            },
            "required": ["repo_path"]
        }
    )(_fallback_get_commit_count)


# expose AVAILABLE_TOOLS for imports
AVAILABLE_TOOLS = generate_available_tools()

__all__ = ["tool", "AVAILABLE_TOOLS", "_tool_registry", "generate_available_tools"]
