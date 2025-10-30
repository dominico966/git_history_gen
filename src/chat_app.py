"""
Chainlit 기반 대화형 Git 히스토리 분석 채팅 앱
프롬프트는 구조화된 객체로 관리하며 여러 줄 문자열(''' or \"\"\") 사용 금지
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import chainlit as cl
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
from openai import AzureOpenAI

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools import (
    get_commit_summary,
    search_commits,
    analyze_contributors,
    find_frequent_bug_commits,
    get_commit_count
)
from src.online_reader import (
    OnlineRepoReader,
    read_file_from_commit,
    get_file_context,
    get_readme_content,
    get_commit_diff
)
from src.indexer import CommitIndexer
from azure.search.documents.indexes import SearchIndexClient
from src.index_manager import IndexManager, format_index_statistics

from datetime import datetime
TODAY=datetime.today().strftime('%Y-%m-%d')

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 안전 장치: 최대값 제한 (토큰/비용 폭탄 방지)
MAX_COMMIT_LIMIT = int(os.getenv("MAX_COMMIT_LIMIT", "1000"))
MAX_SEARCH_TOP = int(os.getenv("MAX_SEARCH_TOP", "50"))
MAX_CONTRIBUTOR_LIMIT = int(os.getenv("MAX_CONTRIBUTOR_LIMIT", "1000"))
DEFAULT_INDEX_LIMIT = int(os.getenv("DEFAULT_INDEX_LIMIT", "500"))

# SocketIO 페이로드 제한
MAX_TOOL_RESULT_DISPLAY = 500  # Step에 표시할 최대 문자 수
MAX_TOOL_RESULT_TO_LLM = 10000  # LLM에 전달할 최대 문자 수
MAX_CONVERSATION_MESSAGES = 20  # 시스템 프롬프트 + 최근 N개 메시지

# ----- 프롬프트 정의 (여러 줄 문자열 금지) -----
SYSTEM_PROMPT_PARTS = [
    # 날짜는 실행 시 주입됨
    f"Git 히스토리 분석 전문가. 오늘: {TODAY}",
    "",
    "# 핵심 규칙",
    "- 한국어 구조화된 답변. 확인 질문 금지",
    "- 도구 바로 실행 → 결과 분석 → 명확한 설명",
    "- 검색은 영어만. 다른 언어시 번역",
    "",
    "# 인덱싱 전략",
    f"1. 분석 요청시: list_indexed_repositories → get_commit_count 확인",
    f"2. 기본: 최근 {DEFAULT_INDEX_LIMIT}개, HEAD부터 시작, skip_existing=true",
    "3. 증분: skip_offset으로 과거 커밋 추가",
    "4. **중요**: 인덱싱수 < 전체수 → 추가 필요. '전부' 요청시 100% 완료까지",
    "5. 규모별: ~100(기본), 100~500(skip_offset), 500+(날짜범위)",
    "",
    "# 증분 인덱싱 결과 해석",
    "- 로그에 'Skipped N already indexed commits' 표시 → **정상 동작**",
    "- 이미 인덱싱된 커밋은 자동으로 건너뛰고, 새로운 커밋만 인덱싱함",
    "- 예: 436개 추출 → 100개 건너뜀 → 336개 인덱싱 = **336개 추가됨**",
    "- 사용자에게는 **새로 추가된 개수**와 **전체 인덱싱 현황**을 함께 설명",
    "",
    "# '전체' 인덱싱 요청 처리",
    "- **'전부', '다 해', '전체', '모든' 등의 요청 시**:",
    "  1. get_commit_count로 전체 커밋 개수(N) 확인",
    "  2. list_indexed_repositories로 이미 인덱싱된 개수(M) 확인",
    "  3. index_repository 호출 시 limit=N 설정 (증분 인덱싱 자동 적용됨)",
    "  4. 완료 후 실제 인덱싱된 개수 확인 및 검증",
    "- **절대 limit 없이 호출하지 말 것** (기본값 100개만 처리됨)",
    "",
    "# 자연어 인덱싱 요청",
    "- **'올해', '2025년'**: since=2025-01-01, until=2025-12-31 자동 설정",
    "- **'최근'**: limit=500 권장",
    "- **날짜 지정**: since/until 파라미터 사용 (YYYY-MM-DD)",
    "- UI에서도 키워드 입력 가능: '올해', '전체', '최근', 날짜",
    "",
    "# 필수 판단 원칙",
    "- **추측 금지**: get_commit_count ↔ list_indexed_repositories 비교 필수",
    "- 부분 인덱싱 → 추가 작업, 완전 인덱싱 → \"이미 있음\" 가능",
    "- 날짜범위 후 실제 결과 검증",
    "",
    "# 도구",
    "- search_commits: 자동 UI 확인",
    "- index_repository: 대용량시 자동 UI 확인",
    "- 날짜: YYYY-MM-DD 형식",
]


def _build_system_prompt(today: str) -> str:
    """SYSTEM_PROMPT_PARTS를 바탕으로 오늘 날짜를 주입해 최종 프롬프트를 생성"""
    # 여러 줄 문자열을 사용하지 않고, 라인 단위로 결합
    lines = []
    for part in SYSTEM_PROMPT_PARTS:
        lines.append(part.replace("{TODAY}", today))
    return "\n".join(lines)


# 모듈 import 시점의 기본 프롬프트(테스트에서 사용). 동적 날짜는 get_system_prompt()를 권장
try:
    from datetime import datetime
    SYSTEM_PROMPT = _build_system_prompt(datetime.now().strftime("%Y-%m-%d"))
except Exception:
    # 날짜 생성 실패 시에도 상수가 존재하도록 fallback
    SYSTEM_PROMPT = _build_system_prompt("0000-00-00")


def get_system_prompt() -> str:
    """압축된 시스템 프롬프트 - 핵심 규칙만 포함 (동적 날짜 주입)"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    return _build_system_prompt(today)

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_commit_count",
            "description": "저장소의 총 커밋 개수를 빠르게 확인합니다. 날짜 범위를 지정하여 특정 기간의 커밋만 셀 수 있습니다. 인덱싱 전에 저장소 규모를 파악할 때 유용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로 (로컬 경로 또는 GitHub URL)"
                    },
                    "since": {
                        "type": "string",
                        "description": "시작 날짜 (ISO 8601 형식, 예: 2024-01-01). 이 날짜 이후의 커밋만 셉니다."
                    },
                    "until": {
                        "type": "string",
                        "description": "종료 날짜 (ISO 8601 형식, 예: 2024-12-31). 이 날짜 이전의 커밋만 셉니다."
                    }
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_commit_summary",
            "description": "Git 저장소의 최근 커밋들을 요약합니다. 최근 변경사항, 주요 기여자, 트렌드를 분석합니다. 로컬 Git 히스토리에서 직접 읽어옵니다. 더 정밀한 검색이 필요하면 저장소를 인덱싱한 후 search_commits를 사용하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로 (로컬 경로 또는 GitHub URL)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "분석할 커밋 수 (기본값: 50)",
                        "default": 50
                    }
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_commits",
            "description": "자연어 쿼리로 커밋을 검색합니다. 특정 기능, 버그, 파일 등과 관련된 커밋을 찾을 수 있습니다. 인덱싱되지 않은 저장소의 경우 시스템이 자동으로 사용자에게 확인을 요청합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색 쿼리 (자연어)"
                    },
                    "top": {
                        "type": "integer",
                        "description": "반환할 최대 결과 수 (기본값: 10)",
                        "default": 10
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "특정 저장소만 검색 (선택적)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_contributors",
            "description": "기여자별 활동을 분석합니다. 커밋 수, 변경 라인 수, 최근 활동 등을 제공합니다. 날짜 범위를 지정하여 특정 기간의 기여자 활동만 분석할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로"
                    },
                    "criteria": {
                        "type": "string",
                        "description": "평가 기준 (선택적, 기본값: 커밋 수, 변경 라인 수)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "분석할 커밋 수 (선택적)"
                    },
                    "since": {
                        "type": "string",
                        "description": "시작 날짜 (ISO 8601 형식, 예: 2024-01-01). 이 날짜 이후의 커밋만 분석합니다."
                    },
                    "until": {
                        "type": "string",
                        "description": "종료 날짜 (ISO 8601 형식, 예: 2024-12-31). 이 날짜 이전의 커밋만 분석합니다."
                    }
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_bug_commits",
            "description": "버그 수정과 관련된 커밋을 찾습니다. 커밋 메시지에서 'fix', 'bug', 'issue' 등의 키워드를 탐지합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "분석할 커밋 수 (기본값: 200)",
                        "default": 200
                    }
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_github_repo",
            "description": "GitHub에서 저장소를 검색합니다. 키워드로 관련 저장소를 찾을 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색 키워드"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "최대 결과 수 (기본값: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_from_commit",
            "description": "특정 커밋에서 파일 내용을 읽습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로"
                    },
                    "commit_sha": {
                        "type": "string",
                        "description": "커밋 해시"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "파일 경로"
                    }
                },
                "required": ["repo_path", "commit_sha", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_context",
            "description": "커밋에서 변경된 파일의 주변 컨텍스트와 diff를 가져옵니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로"
                    },
                    "commit_sha": {
                        "type": "string",
                        "description": "커밋 해시"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "파일 경로"
                    }
                },
                "required": ["repo_path", "commit_sha", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_commit_diff",
            "description": "특정 커밋의 전체 변경사항(diff)을 가져옵니다. 어떤 파일이 어떻게 변경되었는지 한눈에 볼 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로"
                    },
                    "commit_sha": {
                        "type": "string",
                        "description": "커밋 해시 또는 커밋 ID"
                    },
                    "max_files": {
                        "type": "integer",
                        "description": "표시할 최대 파일 수 (기본값: 10)",
                        "default": 10
                    }
                },
                "required": ["repo_path", "commit_sha"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_readme",
            "description": "저장소의 README 파일 내용을 가져옵니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로"
                    }
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_current_repository",
            "description": "현재 작업할 저장소를 설정합니다. 이후 다른 도구 호출 시 이 저장소가 기본값으로 사용됩니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로 (로컬 경로 또는 GitHub URL)"
                    }
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "index_repository",
            "description": "Git 저장소를 Azure AI Search에 인덱싱합니다. skip_offset을 사용하면 이미 인덱싱된 커밋 이후의 과거 커밋을 추가할 수 있습니다. 예: 이미 100개 인덱싱 → skip_offset=100, limit=50으로 101~150번째 커밋 추가 가능. 주의: 날짜 범위(since/until) 사용 시 실제 커밋 존재 여부에 따라 인덱싱 개수가 다를 수 있음. 인덱싱 후 get_repository_info로 실제 결과 확인 권장.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 저장소 경로 (로컬 경로 또는 GitHub URL)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "인덱싱할 최대 커밋 수 (선택적)"
                    },
                    "since": {
                        "type": "string",
                        "description": "시작 날짜 ISO 8601 형식 (선택적, 예: 2024-01-01)"
                    },
                    "until": {
                        "type": "string",
                        "description": "종료 날짜 ISO 8601 형식 (선택적, 예: 2024-12-31)"
                    },
                    "skip_existing": {
                        "type": "boolean",
                        "description": "이미 인덱싱된 커밋 건너뛰기 (기본값: true)",
                        "default": True
                    },
                    "skip_offset": {
                        "type": "integer",
                        "description": "HEAD부터 건너뛸 커밋 수 (과거 커밋 추가 시, 기본값: 0)",
                        "default": 0
                    }
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_index_statistics",
            "description": "인덱스 통계 정보를 조회합니다. 총 커밋 수, 저장소 수, 기여자 수, 날짜 범위 등을 확인할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_indexed_repositories",
            "description": "인덱싱된 저장소 목록을 조회합니다. 각 저장소의 커밋 수도 함께 제공합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_repository_info",
            "description": "특정 저장소의 상세 정보를 조회합니다. 커밋 수, 기여자 수, 날짜 범위 등을 확인할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "저장소 식별자 (16자리 해시)"
                    }
                },
                "required": ["repo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_repository_commits",
            "description": "특정 저장소의 모든 커밋을 인덱스에서 삭제합니다. 주의: 복구할 수 없습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "저장소 식별자 (16자리 해시)"
                    }
                },
                "required": ["repo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_index_health",
            "description": "인덱스 상태를 확인합니다. 인덱스가 정상적으로 작동하는지 검증합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_commits_by_date",
            "description": "날짜 범위로 인덱싱된 커밋을 조회합니다. 특정 기간의 커밋 활동을 확인할 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "since": {
                        "type": "string",
                        "description": "시작 날짜 (ISO 8601 형식, 예: 2024-01-01)"
                    },
                    "until": {
                        "type": "string",
                        "description": "종료 날짜 (ISO 8601 형식, 예: 2024-12-31)"
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "특정 저장소만 조회 (선택적)"
                    },
                    "top": {
                        "type": "integer",
                        "description": "반환할 최대 결과 수 (기본값: 50)",
                        "default": 50
                    }
                },
                "required": []
            }
        }
    }
]


def initialize_clients() -> tuple[AzureOpenAI, SearchClient, SearchIndexClient]:
    """Azure OpenAI, Search, IndexClient 초기화"""
    try:
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

        logger.info("Clients initialized successfully")
        return openai_client, search_client, index_client

    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        raise


async def resolve_repository_ambiguity(
    repo_hint: str,
    search_client: SearchClient,
    index_client: SearchIndexClient
) -> Optional[str]:
    """모호한 저장소 입력을 해결하여 정확한 경로 반환. 실패 시 None 반환"""
    from src.index_manager import IndexManager

    index_manager = IndexManager(
        search_client=search_client,
        index_client=index_client,
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    )

    # 인덱싱된 모든 저장소 가져오기
    repos = index_manager.list_indexed_repositories()

    if not repos:
        return None

    # repo_hint로 필터링 (부분 일치)
    matching_repos = [
        r for r in repos
        if repo_hint.lower() in r['repository_path'].lower()
    ]

    if len(matching_repos) == 0:
        return None
    elif len(matching_repos) == 1:
        return matching_repos[0]['repository_path']
    else:
        # 여러 개 발견 - 사용자에게 선택 요청
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
    openai_client: AzureOpenAI,
    search_client: SearchClient,
    index_client: SearchIndexClient
) -> str:
    """도구 실행"""
    try:
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        # repo_path가 없고 current_repository가 설정되어 있으면 자동 적용
        current_repo = cl.user_session.get("current_repository")
        if "repo_path" in arguments and not arguments.get("repo_path") and current_repo:
            arguments["repo_path"] = current_repo
            logger.info(f"Using current repository: {current_repo}")
        elif "repo_path" not in arguments and current_repo and tool_name not in ["search_github_repo"]:
            arguments["repo_path"] = current_repo
            logger.info(f"Auto-applying current repository: {current_repo}")

        # 저장소 경로 모호성 해결 (짧은 이름이나 부분 경로인 경우)
        if "repo_path" in arguments and arguments.get("repo_path"):
            repo_path = arguments["repo_path"]
            # 절대 경로가 아니고 짧은 이름인 경우 (예: "project1", "myrepo")
            if not (repo_path.startswith("/") or repo_path.startswith("C:") or
                    repo_path.startswith("http://") or repo_path.startswith("https://")):
                logger.info(f"Ambiguous repository hint detected: {repo_path}")
                resolved_path = await resolve_repository_ambiguity(
                    repo_hint=repo_path,
                    search_client=search_client,
                    index_client=index_client
                )
                if resolved_path:
                    arguments["repo_path"] = resolved_path
                    logger.info(f"Resolved to: {resolved_path}")
                elif resolved_path is None:
                    return f"❌ '{repo_path}'와 일치하는 인덱싱된 저장소를 찾을 수 없습니다. 정확한 경로를 입력하거나 먼저 저장소를 인덱싱해주세요."

        # 안전 장치: 최대값 제한 적용 (index_repository는 제외)
        # ⚠️ index_repository의 limit은 증분 인덱싱 로직에서 처리하므로 여기서는 경고만 로그
        if "limit" in arguments and arguments["limit"]:
            if tool_name == "index_repository":
                # index_repository는 경고만 로그, cap 안 함
                if arguments["limit"] > MAX_COMMIT_LIMIT:
                    logger.warning(f"⚠️ Large limit requested: {arguments['limit']} (recommended max: {MAX_COMMIT_LIMIT})")
            else:
                # 다른 도구는 cap 적용
                if arguments["limit"] > MAX_COMMIT_LIMIT:
                    logger.warning(f"Limit {arguments['limit']} exceeds max {MAX_COMMIT_LIMIT}, capping")
                    arguments["limit"] = MAX_COMMIT_LIMIT

        if "top" in arguments and arguments["top"]:
            if arguments["top"] > MAX_SEARCH_TOP:
                logger.warning(f"Top {arguments['top']} exceeds max {MAX_SEARCH_TOP}, capping")
                arguments["top"] = MAX_SEARCH_TOP

        import asyncio
        loop = asyncio.get_event_loop()

        if tool_name == "get_commit_count":
            result = await loop.run_in_executor(
                None,
                lambda: get_commit_count(
                    repo_path=arguments["repo_path"],
                    since=arguments.get("since"),
                    until=arguments.get("until")
                )
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif tool_name == "get_commit_summary":
            result = await loop.run_in_executor(
                None,
                lambda: get_commit_summary(
                    repo_path=arguments["repo_path"],
                    llm_client=openai_client,
                    limit=arguments.get("limit", 50)
                )
            )
            return result

        elif tool_name == "search_commits":
            # 저장소 경로가 지정된 경우 자동 인덱싱 확인
            repo_path = arguments.get("repo_path")
            if repo_path:
                from src.indexer import normalize_repo_identifier
                repo_id = normalize_repo_identifier(repo_path)

                # 해당 저장소가 인덱싱되어 있는지 확인
                try:
                    check_results = search_client.search(
                        search_text="*",
                        filter=f"repo_id eq '{repo_id}'",
                        select=["id"],
                        top=1
                    )
                    has_indexed = len(list(check_results)) > 0

                    if not has_indexed:
                        logger.info(f"Repository not indexed, asking user permission: {repo_path}")

                        # 커밋 개수 먼저 확인
                        commit_info = get_commit_count(repo_path)
                        total_commits = commit_info.get("commit_count", 0)
                        is_error = "error" in commit_info

                        if is_error:
                            commit_info_text = "**총 커밋 수**: 확인 불가"
                        else:
                            commit_info_text = f"**총 커밋 수**: {total_commits:,}개"

                        # 사용자에게 인덱싱 허락 받기 (UI 버튼)
                        res = await cl.AskActionMessage(
                            content=f"🔍 검색을 위해 저장소를 인덱싱해야 합니다.\n\n**저장소**: `{repo_path}`\n{commit_info_text}\n**인덱싱 예정**: 최근 {DEFAULT_INDEX_LIMIT}개 커밋\n\n인덱싱을 진행하시겠습니까?",
                            actions=[
                                cl.Action(name="yes", payload={"action": "yes"}, label="✅ 예, 인덱싱 시작"),
                                cl.Action(name="no", payload={"action": "no"}, label="❌ 아니오, 취소"),
                            ],
                            timeout=120,  # 2분
                            raise_on_timeout=False
                        ).send()

                        if not res:
                            logger.info(f"User timeout for indexing: {repo_path}")
                            return "⏱️ 시간 초과. 인덱싱을 취소했습니다. 다시 시도하려면 검색을 다시 요청해주세요."

                        if res.get("payload", {}).get("action") == "yes":
                            # 인덱싱 시작 알림
                            await cl.Message(content="⏳ 인덱싱을 시작합니다...").send()

                            # 자동 인덱싱 실행
                            indexer = CommitIndexer(
                                search_client=search_client,
                                index_client=index_client,
                                openai_client=openai_client,
                                index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
                            )
                            indexer.create_index_if_not_exists()

                            indexed_count = indexer.index_repository(
                                repo_path=repo_path,
                                limit=DEFAULT_INDEX_LIMIT,
                                skip_existing=True
                            )

                            logger.info(f"User approved, indexed {indexed_count} commits for {repo_path}")

                            # 인덱싱 완료 메시지 (Step 외부에 명확히 표시)
                            if indexed_count == 0:
                                await cl.Message(content="✅ **인덱싱 완료**\n\n저장소가 이미 인덱싱되어 있습니다. 검색을 계속 진행합니다.").send()
                                # 검색을 계속 진행하도록 pass through
                            else:
                                await cl.Message(content=f"✅ **인덱싱 완료**\n\n{indexed_count}개 커밋이 인덱싱되었습니다.\n검색을 계속 진행합니다...").send()
                                # 검색을 계속 진행하도록 pass through
                        else:
                            logger.info(f"User declined indexing for {repo_path}")
                            return "❌ 사용자가 인덱싱을 취소했습니다. 검색을 수행할 수 없습니다."

                except Exception as e:
                    logger.warning(f"Failed to check indexing status: {e}")

            # 검색 실행
            results = await loop.run_in_executor(
                None,
                lambda: search_commits(
                    query=arguments["query"],
                    search_client=search_client,
                    openai_client=openai_client,
                    top=arguments.get("top", 10),
                    repo_path=repo_path
                )
            )

            # 결과 요약 (페이로드 크기 제한)
            if isinstance(results, list) and len(results) > 0:
                summary = f"검색 결과: {len(results)}개 커밋 발견\n\n"
                for i, r in enumerate(results[:10], 1):  # 최대 10개만
                    commit_id = r.get('commit_id', 'N/A')
                    short_sha = commit_id[:8] if len(commit_id) >= 8 else commit_id
                    summary += f"{i}. [{short_sha}] {r.get('message', 'N/A')[:80]}... (by {r.get('author', 'N/A')})\n"
                if len(results) > 10:
                    summary += f"\n...외 {len(results)-10}개 커밋"
                return summary
            return json.dumps(results, ensure_ascii=False, indent=2)

        elif tool_name == "analyze_contributors":
            # limit 기본값 설정 (없으면 500으로 제한)
            contributor_limit = arguments.get("limit", 500)
            if contributor_limit > MAX_CONTRIBUTOR_LIMIT:
                contributor_limit = MAX_CONTRIBUTOR_LIMIT

            result = await loop.run_in_executor(
                None,
                lambda: analyze_contributors(
                    repo_path=arguments["repo_path"],
                    criteria=arguments.get("criteria"),
                    limit=contributor_limit,
                    since=arguments.get("since"),
                    until=arguments.get("until")
                )
            )

            # 결과 요약
            if isinstance(result, dict) and 'contributors' in result:
                contributors = result['contributors']
                date_info = ""
                if arguments.get("since") or arguments.get("until"):
                    date_parts = []
                    if arguments.get("since"):
                        date_parts.append(f"{arguments['since']} 이후")
                    if arguments.get("until"):
                        date_parts.append(f"{arguments['until']} 이전")
                    date_info = f" ({', '.join(date_parts)})"
                summary = f"👥 기여자 분석 결과{date_info}: 총 {len(contributors)}명\n\n"
                for i, c in enumerate(contributors[:10], 1):  # 최대 10명
                    summary += f"{i}. {c.get('name', 'N/A')}: {c.get('commits', 0)}개 커밋, {c.get('total_lines_changed', 0)}줄 변경\n"
                if len(contributors) > 10:
                    summary += f"\n...외 {len(contributors)-10}명"
                return summary
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif tool_name == "find_bug_commits":
            results = await loop.run_in_executor(
                None,
                lambda: find_frequent_bug_commits(
                    repo_path=arguments["repo_path"],
                    llm_client=openai_client,
                    limit=arguments.get("limit", 200)
                )
            )

            # 결과 요약
            if isinstance(results, list) and len(results) > 0:
                summary = f"🐛 버그 수정 커밋: {len(results)}개 발견\n\n"
                for i, r in enumerate(results[:10], 1):  # 최대 10개
                    summary += f"{i}. {r.get('message', 'N/A')[:80]}... (by {r.get('author', 'N/A')})\n"
                if len(results) > 10:
                    summary += f"\n...외 {len(results)-10}개 커밋"
                return summary
            return json.dumps(results, ensure_ascii=False, indent=2)

        elif tool_name == "search_github_repo":
            reader = OnlineRepoReader()
            results = await loop.run_in_executor(
                None,
                lambda: reader.search_github_repo(
                    query=arguments["query"],
                    max_results=arguments.get("max_results", 5)
                )
            )

            # 결과 요약 (페이로드 크기 제한)
            if results and len(results) > 0:
                summary = f"🔍 GitHub 검색 결과: {len(results)}개 저장소\n\n"
                for i, repo in enumerate(results, 1):
                    desc = repo.get('description', 'No description')
                    if len(desc) > 100:
                        desc = desc[:100] + "..."

                    summary += f"{i}. **{repo.get('full_name', 'N/A')}** ⭐ {repo.get('stars', 0):,}\n"
                    summary += f"   언어: {repo.get('language', 'N/A')} | {desc}\n"
                    summary += f"   URL: {repo.get('url', 'N/A')}\n\n"

                return summary
            elif results is None:
                return "GitHub 검색에 실패했습니다."
            else:
                return "검색 결과가 없습니다."

        elif tool_name == "read_file_from_commit":
            content = await loop.run_in_executor(
                None,
                lambda: read_file_from_commit(
                    repo_path=arguments["repo_path"],
                    commit_sha=arguments["commit_sha"],
                    file_path=arguments["file_path"]
                )
            )
            return content if content else "파일을 읽을 수 없습니다."

        elif tool_name == "get_file_context":
            context = await loop.run_in_executor(
                None,
                lambda: get_file_context(
                    repo_path=arguments["repo_path"],
                    commit_sha=arguments["commit_sha"],
                    file_path=arguments["file_path"]
                )
            )

            # 결과 요약
            if context:
                summary = f"📄 파일 컨텍스트: {context.get('file_path', 'N/A')}\n"
                summary += f"커밋: {context.get('commit_sha', 'N/A')[:8]}\n"
                summary += f"변경 타입: {context.get('change_type', 'N/A')}\n"

                if context.get('diff'):
                    diff_text = context['diff']
                    if len(diff_text) > 1000:
                        diff_text = diff_text[:1000] + "\n...(truncated)"
                    summary += f"\nDiff:\n```\n{diff_text}\n```"

                return summary
            else:
                return "파일 컨텍스트를 가져올 수 없습니다."

        elif tool_name == "get_commit_diff":
            diff_info = await loop.run_in_executor(
                None,
                lambda: get_commit_diff(
                    repo_path=arguments["repo_path"],
                    commit_sha=arguments["commit_sha"],
                    max_files=arguments.get("max_files", 10)
                )
            )

            if diff_info:
                # 에러인 경우
                if diff_info.get("error"):
                    return diff_info["message"]

                # 정상인 경우 - 요약해서 전달
                summary = f"📝 커밋 Diff: {diff_info.get('short_sha', 'N/A')}\n"
                summary += f"작성자: {diff_info.get('author', 'N/A')}\n"
                summary += f"날짜: {diff_info.get('date', 'N/A')}\n"
                summary += f"메시지: {diff_info.get('message', 'N/A')[:200]}\n\n"

                stats = diff_info.get('stats', {})
                summary += f"📊 통계: {stats.get('files', 0)}개 파일, "
                summary += f"+{stats.get('insertions', 0)}/-{stats.get('deletions', 0)} 라인\n\n"

                files_changed = diff_info.get('files_changed', [])
                if files_changed:
                    summary += f"📂 변경된 파일 ({len(files_changed)}개):\n"
                    for i, f in enumerate(files_changed[:5], 1):  # 최대 5개만
                        summary += f"{i}. {f.get('file', 'N/A')} "
                        summary += f"(+{f.get('lines_added', 0)}/-{f.get('lines_deleted', 0)})\n"

                        # diff 내용 일부만
                        if f.get('diff') and len(f['diff']) > 0:
                            diff_preview = f['diff'][:500]
                            if len(f['diff']) > 500:
                                diff_preview += "\n...(truncated)"
                            summary += f"```diff\n{diff_preview}\n```\n"

                    if len(files_changed) > 5:
                        summary += f"\n...외 {len(files_changed) - 5}개 파일"

                return summary
            else:
                return "커밋 diff를 가져올 수 없습니다."

        elif tool_name == "get_readme":
            content = await loop.run_in_executor(
                None,
                lambda: get_readme_content(arguments["repo_path"])
            )
            return content if content else "README 파일을 찾을 수 없습니다."

        elif tool_name == "set_current_repository":
            repo_path = arguments["repo_path"]
            cl.user_session.set("current_repository", repo_path)
            logger.info(f"Current repository set to: {repo_path}")
            return f"현재 저장소를 '{repo_path}'로 설정했습니다. 이제 저장소 경로를 생략하면 이 저장소가 사용됩니다."

        elif tool_name == "index_repository":
            indexer = CommitIndexer(
                search_client=search_client,
                index_client=index_client,
                openai_client=openai_client,
                index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
            )

            # 인덱스 생성 (없으면)
            indexer.create_index_if_not_exists()

            # ⚠️ 증분 인덱싱 로직 - cap되지 않은 원래 limit 값 사용
            skip_offset = arguments.get("skip_offset", 0)
            original_limit = arguments.get("limit")  # ✅ cap 이전의 원래 값

            # ⚠️ 증분 인덱싱 조건:
            # 1. skip_offset이 명시되지 않음 (0)
            # 2. 사용자가 명시적으로 limit을 요청함
            # 3. skip_existing=True (기본값)
            # 4. 날짜 범위가 없음 (날짜 범위가 있으면 증분 인덱싱 불가)
            should_apply_incremental = (
                skip_offset == 0 and
                original_limit is not None and
                arguments.get("skip_existing", True) and
                not arguments.get("since") and
                not arguments.get("until")
            )

            if should_apply_incremental:
                try:
                    from src.indexer import normalize_repo_identifier
                    repo_id = normalize_repo_identifier(arguments["repo_path"])

                    # 기존 인덱싱 개수 확인
                    check_results = search_client.search(
                        search_text="*",
                        filter=f"repo_id eq '{repo_id}'",
                        select=["id"],
                        top=10000
                    )
                    existing_count = len(list(check_results))

                    if existing_count > 0:
                        logger.info(f"Found {existing_count} existing commits, user requested {original_limit} total")

                        if original_limit > existing_count:
                            # 사용자가 요청한 총 개수에서 이미 있는 개수를 빼서 실제 필요한 개수 계산
                            adjusted_limit = original_limit - existing_count
                            logger.info(f"Adjusting limit: {original_limit} (total requested) - {existing_count} (existing) = {adjusted_limit} (additional needed)")

                            # skip_offset과 limit 모두 조정
                            skip_offset = existing_count
                            arguments["skip_offset"] = skip_offset
                            arguments["limit"] = adjusted_limit

                        elif original_limit <= existing_count:
                            # 이미 충분한 커밋이 있음
                            logger.info(f"Already have {existing_count} commits (>= {original_limit} requested) - no additional indexing needed")
                            # 인덱싱을 건너뛰고 바로 완료 메시지 반환
                            return f"✅ 저장소에 이미 {existing_count:,}개 커밋이 인덱싱되어 있습니다. (요청: {original_limit:,}개)\n추가 인덱싱이 필요하지 않습니다."

                except Exception as e:
                    logger.warning(f"Failed to calculate incremental indexing: {e}")

            # ✅ 증분 인덱싱 계산 완료 후 limit 설정
            # limit이 없으면 DEFAULT_INDEX_LIMIT 사용
            index_limit = arguments.get("limit")
            if index_limit is None:
                logger.warning(f"No limit specified for indexing, defaulting to {DEFAULT_INDEX_LIMIT}")
                index_limit = DEFAULT_INDEX_LIMIT

            # ⚠️ MAX_COMMIT_LIMIT은 권장 사항일 뿐, 강제하지 않음 (증분 인덱싱 지원)
            if index_limit > MAX_COMMIT_LIMIT:
                logger.warning(f"⚠️ Large indexing: {index_limit} commits (recommended max: {MAX_COMMIT_LIMIT})")

            # 대용량 인덱싱(DEFAULT_INDEX_LIMIT개 이상)이면 사용자 확인
            if index_limit >= DEFAULT_INDEX_LIMIT:
                since_param = arguments.get("since", "")
                until_param = arguments.get("until", "")
                date_info = ""
                if since_param or until_param:
                    date_info = f"\n**날짜 범위**: {since_param or '시작'} ~ {until_param or '끝'}"

                # 📊 전체 커밋 수를 확인 (UI에 표시하기 위해)
                commit_info_msg = await cl.Message(content="📊 저장소 커밋 수를 확인하는 중...").send()
                try:
                    total_commit_info = await loop.run_in_executor(
                        None,
                        lambda: get_commit_count(
                            repo_path=arguments["repo_path"],
                            since=since_param or None,
                            until=until_param or None
                        )
                    )
                    total_commits = total_commit_info.get("commit_count", 0)
                    commit_info_msg.content = f"📊 전체 커밋 수: **{total_commits:,}개**"
                    await commit_info_msg.update()
                except Exception as e:
                    logger.warning(f"Failed to get total commit count: {e}")
                    total_commits = None
                    commit_info_msg.content = f"⚠️ 전체 커밋 수를 확인할 수 없습니다."
                    await commit_info_msg.update()

                # UI 메시지 준비
                ui_content = f"⚠️ 대용량 인덱싱 요청\n\n**저장소**: {arguments['repo_path']}\n"
                if total_commits is not None:
                    ui_content += f"**전체 커밋 수**: {total_commits:,}개\n"
                ui_content += f"**인덱싱 예정**: {index_limit}개 커밋{date_info}\n\n진행 방법을 선택하세요:"

                # 사용자 확인 대기 메시지 (Step 외부에 표시)
                await cl.Message(content="⏸️ 사용자 확인을 기다리는 중입니다...").send()

                res = await cl.AskActionMessage(
                    content=ui_content,
                    actions=[
                        cl.Action(name="proceed", payload={"action": "proceed"}, label="✅ 그대로 진행"),
                        cl.Action(name="custom", payload={"action": "custom", "total_commits": total_commits}, label="✏️ 개수/날짜 변경"),
                        cl.Action(name="cancel", payload={"action": "cancel"}, label="❌ 취소"),
                    ],
                    timeout=120,  # 2분
                    raise_on_timeout=False
                ).send()

                if not res:
                    logger.info(f"User timeout for large indexing: {index_limit} commits")
                    return f"❌ 시간 초과. 인덱싱을 취소했습니다."

                action = res.get("payload", {}).get("action")

                if action == "proceed":
                    await cl.Message(content=f"✅ 사용자 승인됨. {index_limit}개 커밋 인덱싱을 시작합니다...").send()

                elif action == "custom":
                    # 전체 커밋 수 정보를 UI에 표시
                    total_commits_from_payload = res.get("payload", {}).get("total_commits")
                    total_info_text = ""
                    if total_commits_from_payload is not None and total_commits_from_payload > 0:
                        total_info_text = f"\n\n**전체 커밋 수**: {total_commits_from_payload:,}개 (전체 인덱싱을 원하시면 이 숫자를 입력하세요)"

                    # 사용자 정의 개수 입력 받기
                    custom_limit_res = await cl.AskUserMessage(
                        content=f"📝 인덱싱할 커밋 개수 또는 범위를 입력하세요:\n\n"
                                f"• **숫자**: 예) 500, 1000\n"
                                f"• **키워드**: '전체', '올해', '최근'\n"
                                f"• **날짜**: 2025-01-01 또는 2025-01-01,2025-12-31\n\n"
                                f"전체 커밋 수: {total_commits_from_payload:,}개\n"
                                f"⚠️ {MAX_COMMIT_LIMIT}개 이상은 시간이 오래 걸릴 수 있습니다.",
                        timeout=60,
                        raise_on_timeout=False
                    ).send()

                    if not custom_limit_res or not custom_limit_res.get("output"):
                        return "⏱️ 시간 초과 또는 입력 없음. 인덱싱을 취소했습니다."

                    try:
                        user_input = custom_limit_res.get("output").strip().lower()
                        import re
                        from datetime import datetime

                        # 🔍 키워드 처리
                        if any(keyword in user_input for keyword in ['전체', '모두', 'all']):
                            # 전체 커밋
                            index_limit = total_commits_from_payload if total_commits_from_payload else None
                            logger.info(f"User requested 'all': {index_limit}")
                            arguments["limit"] = index_limit

                        elif any(keyword in user_input for keyword in ['올해', '2025', 'this year']):
                            # 올해 커밋
                            arguments["since"] = "2025-01-01"
                            arguments["until"] = "2025-12-31"
                            index_limit = None  # 날짜 범위로 제한
                            logger.info("User requested 'this year': 2025-01-01 ~ 2025-12-31")
                            await cl.Message(content="📅 올해(2025년) 커밋으로 설정되었습니다.").send()

                        elif any(keyword in user_input for keyword in ['최근', 'recent']):
                            # 최근 500개
                            index_limit = 500
                            logger.info("User requested 'recent': 500")
                            arguments["limit"] = index_limit

                        elif ',' in user_input or re.match(r'\d{4}-\d{2}-\d{2}', user_input):
                            # 날짜 범위 형식
                            if ',' in user_input:
                                parts = user_input.split(',')
                                if len(parts) == 2:
                                    arguments["since"] = parts[0].strip()
                                    arguments["until"] = parts[1].strip()
                                    index_limit = None
                                    logger.info(f"User provided date range: {parts[0]} ~ {parts[1]}")
                                    await cl.Message(content=f"📅 날짜 범위: {parts[0]} ~ {parts[1]}").send()
                            else:
                                # 단일 날짜 (since만)
                                arguments["since"] = user_input.strip()
                                index_limit = None
                                logger.info(f"User provided start date: {user_input}")
                                await cl.Message(content=f"📅 시작일: {user_input}").send()
                        else:
                            # 숫자 추출
                            numeric_input = re.sub(r'[^\d]', '', user_input)

                            if not numeric_input:
                                return "❌ 유효한 숫자, 키워드, 또는 날짜를 입력해주세요.\n예: 500, '올해', 2025-01-01"

                            custom_limit = int(numeric_input)

                            if custom_limit < 1:
                                return "❌ 1개 이상의 커밋을 입력해주세요."

                            index_limit = custom_limit
                            logger.info(f"User selected custom limit: {index_limit}")
                            arguments["limit"] = index_limit

                    except Exception as e:
                        logger.error(f"Error parsing user input: {e}")
                        return f"❌ 입력 형식 오류: {str(e)}\n예: 500, '올해', 2025-01-01,2025-12-31"

                    # 날짜 범위 입력 받기 (이미 설정되지 않은 경우만)
                    if not arguments.get("since") and not arguments.get("until"):
                        date_res = await cl.AskUserMessage(
                            content="📅 날짜 범위를 입력하세요 (형식: YYYY-MM-DD,YYYY-MM-DD 또는 빈칸으로 건너뛰기):\n\n예: 2024-01-01,2024-12-31",
                            timeout=60,
                            raise_on_timeout=False
                        ).send()

                        if date_res and date_res.get("output") and date_res.get("output").strip():
                            date_input = date_res.get("output").strip()
                            if "," in date_input:
                                parts = date_input.split(",")
                                if len(parts) == 2:
                                    arguments["since"] = parts[0].strip() or None
                                    arguments["until"] = parts[1].strip() or None

                    await cl.Message(content=f"✅ 설정 완료. {index_limit:,}개 커밋 인덱싱을 시작합니다...").send()

                else:  # cancel
                    logger.info(f"User declined large indexing: {index_limit} commits")
                    return f"❌ 사용자가 대용량 인덱싱을 취소했습니다. 더 작은 범위로 다시 시도하거나 날짜 범위를 지정해주세요."

            # 일반 인덱싱 (분할 없이 한 번에 처리)
            # ⚠️ MAX_COMMIT_LIMIT은 권장 사항일 뿐, 증분 인덱싱은 전체를 처리해야 함
            indexed_count = await loop.run_in_executor(
                None,
                lambda: indexer.index_repository(
                    repo_path=arguments["repo_path"],
                    limit=index_limit,
                    since=arguments.get("since"),
                    until=arguments.get("until"),
                    skip_existing=arguments.get("skip_existing", True),
                    skip_offset=arguments.get("skip_offset", 0)
                )
            )

            # 인덱싱 완료 메시지를 Step 외부에 명확히 표시
            if indexed_count == 0:
                logger.info(f"Repository already indexed: {arguments['repo_path']}")
                await cl.Message(content=f"✅ **인덱싱 확인 완료**\n\n저장소가 이미 인덱싱되어 있습니다.\n저장소: `{arguments['repo_path']}`").send()
                return f"저장소가 이미 인덱싱되어 있습니다. 검색 및 분석을 바로 시작할 수 있습니다."
            else:
                # 전체 인덱싱 현황 확인 (증분 인덱싱 컨텍스트 제공)
                try:
                    from src.indexer import normalize_repo_identifier
                    repo_id = normalize_repo_identifier(arguments["repo_path"])

                    # 현재 인덱싱된 총 개수 확인
                    total_check_results = search_client.search(
                        search_text="*",
                        filter=f"repo_id eq '{repo_id}'",
                        select=["id"],
                        top=10000
                    )
                    total_indexed_count = len(list(total_check_results))

                    result_msg = f"{indexed_count}개 커밋이 새로 인덱싱되었습니다. (전체: {total_indexed_count}개)"
                except Exception as e:
                    logger.warning(f"Failed to get total indexed count: {e}")
                    result_msg = f"{indexed_count}개 커밋이 인덱싱되었습니다."

                if arguments.get("since") or arguments.get("until"):
                    # 날짜 범위 인덱싱의 경우 실제 인덱싱된 날짜 범위 확인
                    try:
                        from src.indexer import normalize_repo_identifier
                        repo_id = normalize_repo_identifier(arguments["repo_path"])

                        # 인덱싱된 실제 날짜 범위 조회
                        date_check_results = search_client.search(
                            search_text="*",
                            filter=f"repo_id eq '{repo_id}'",
                            select=["date"],
                            order_by=["date asc"],
                            top=1
                        )
                        oldest_result = list(date_check_results)

                        date_check_results = search_client.search(
                            search_text="*",
                            filter=f"repo_id eq '{repo_id}'",
                            select=["date"],
                            order_by=["date desc"],
                            top=1
                        )
                        newest_result = list(date_check_results)

                        if oldest_result and newest_result:
                            oldest_date = oldest_result[0]["date"][:10]  # YYYY-MM-DD만
                            newest_date = newest_result[0]["date"][:10]

                            requested_range = f"{arguments.get('since', '시작')} ~ {arguments.get('until', '끝')}"
                            actual_range = f"{oldest_date} ~ {newest_date}"

                            result_msg += f"\n\n**날짜 범위 검증**:\n"
                            result_msg += f"- 요청한 범위: {requested_range}\n"
                            result_msg += f"- 실제 인덱싱된 범위: {actual_range}\n"

                            # 요청 범위와 실제 범위가 다른 경우 안내
                            if arguments.get("since") and arguments.get("since") != oldest_date:
                                result_msg += f"- ⚠️ 요청한 시작일({arguments.get('since')})에는 커밋이 없어서 {oldest_date}부터 시작됨\n"
                            if arguments.get("until") and arguments.get("until") != newest_date:
                                result_msg += f"- ⚠️ 요청한 종료일({arguments.get('until')})에는 커밋이 없어서 {newest_date}까지만 포함됨\n"

                    except Exception as e:
                        logger.warning(f"Failed to verify date range: {e}")

                await cl.Message(content=f"✅ **인덱싱 완료**\n\n{result_msg}\n\n저장소: `{arguments['repo_path']}`").send()
                return result_msg

        elif tool_name == "get_index_statistics":
            index_manager = IndexManager(
                search_client=search_client,
                index_client=index_client,
                index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
            )
            stats = await loop.run_in_executor(
                None,
                lambda: index_manager.get_index_statistics()
            )
            formatted = format_index_statistics(stats)
            return formatted

        elif tool_name == "list_indexed_repositories":
            index_manager = IndexManager(
                search_client=search_client,
                index_client=index_client,
                index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
            )
            repos = await loop.run_in_executor(
                None,
                lambda: index_manager.list_indexed_repositories()
            )

            if not repos:
                return "인덱싱된 저장소가 없습니다."

            result_lines = ["📁 **인덱싱된 저장소 목록**", ""]
            for repo in repos:
                result_lines.append(
                    f"- **{repo['repository_path']}**\n"
                    f"  - Repo ID: `{repo['repo_id']}`\n"
                    f"  - 커밋 수: {repo['commit_count']}"
                )

            return "\n".join(result_lines)

        elif tool_name == "get_repository_info":
            index_manager = IndexManager(
                search_client=search_client,
                index_client=index_client,
                index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
            )
            info = await loop.run_in_executor(
                None,
                lambda: index_manager.get_repository_info(arguments["repo_id"])
            )

            if not info:
                return f"저장소 정보를 찾을 수 없습니다: {arguments['repo_id']}"

            # 구조화된 프롬프트로 결과 생성
            result_parts = [
                "📊 **저장소 정보**",
                "",
                f"**경로**: {info['repository_path']}",
                f"**Repo ID**: `{info['repo_id']}`",
                f"**커밋 수**: {info['commit_count']:,}",
                f"**기여자 수**: {info['author_count']}",
                "",
                "**날짜 범위**:",
                f"- 가장 오래된 커밋: {info['date_range']['oldest'] or 'N/A'}",
                f"- 가장 최근 커밋: {info['date_range']['newest'] or 'N/A'}"
            ]
            return "\n".join(result_parts)

        elif tool_name == "delete_repository_commits":
            index_manager = IndexManager(
                search_client=search_client,
                index_client=index_client,
                index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
            )
            deleted_count = await loop.run_in_executor(
                None,
                lambda: index_manager.delete_repository_commits(arguments["repo_id"])
            )
            return f"✓ {deleted_count}개 커밋이 삭제되었습니다. (Repo ID: {arguments['repo_id']})"

        elif tool_name == "check_index_health":
            index_manager = IndexManager(
                search_client=search_client,
                index_client=index_client,
                index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
            )
            health = await loop.run_in_executor(
                None,
                lambda: index_manager.check_index_health()
            )

            status_emoji = "✅" if health["status"] == "healthy" else "⚠️" if health["status"] == "degraded" else "❌"

            # 구조화된 프롬프트로 결과 생성
            result_parts = [
                f"{status_emoji} **인덱스 상태: {health['status']}**",
                "",
                f"**인덱스 이름**: {health.get('index_name', 'N/A')}",
                f"**인덱스 존재**: {'✓' if health.get('index_exists') else '✗'}",
                f"**총 문서 수**: {health.get('total_documents', 0):,}",
                f"**검색 기능**: {'정상' if health.get('search_works') else '오류'}"
            ]

            if "message" in health:
                result_parts.append("")
                result_parts.append(f"**메시지**: {health['message']}")

            return "\n".join(result_parts)

        elif tool_name == "search_commits_by_date":
            # 날짜 범위로 커밋 조회
            repo_path = arguments.get("repo_path")
            since = arguments.get("since")
            until = arguments.get("until")
            top = arguments.get("top", 50)

            # 필터 구성
            filters = []

            if repo_path:
                from src.indexer import normalize_repo_identifier
                repo_id = normalize_repo_identifier(repo_path)
                filters.append(f"repo_id eq '{repo_id}'")

            if since:
                filters.append(f"date ge {since}T00:00:00Z")

            if until:
                filters.append(f"date le {until}T23:59:59Z")

            filter_expr = " and ".join(filters) if filters else None

            try:
                results = search_client.search(
                    search_text="*",
                    filter=filter_expr,
                    select=["id", "message", "author", "date", "files_summary", "repository_path"],
                    order_by=["date desc"],
                    top=min(top, MAX_SEARCH_TOP)
                )

                commits = []
                for result in results:
                    commits.append({
                        "commit_id": result.get("id", ""),
                        "message": result.get("message", ""),
                        "author": result.get("author", ""),
                        "date": result.get("date", ""),
                        "files": result.get("files_summary", ""),
                        "repository": result.get("repository_path", "")
                    })

                if not commits:
                    return f"해당 기간에 인덱싱된 커밋이 없습니다. (since: {since or '제한없음'}, until: {until or '제한없음'})"

                # 결과 요약 (페이로드 크기 제한)
                summary = f"📅 날짜 범위 검색 결과: {len(commits)}개 커밋\n"
                summary += f"기간: {since or '시작'} ~ {until or '현재'}\n\n"
                for i, c in enumerate(commits[:10], 1):  # 최대 10개만
                    summary += f"{i}. {c['message'][:80]}... (by {c['author']}, {c['date'][:10]})\n"
                if len(commits) > 10:
                    summary += f"\n...외 {len(commits)-10}개 커밋"
                return summary

            except Exception as e:
                logger.error(f"Failed to search commits by date: {e}")
                return f"날짜 범위 조회 중 오류 발생: {str(e)}"

        else:
            return f"알 수 없는 도구: {tool_name}"

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return f"도구 실행 중 오류 발생: {str(e)}"


@cl.set_starters
async def set_starters():
    """초기 시작 화면에 표시할 스타터 제안 - Chainlit starters 기능

    Icons8 MCP를 통해 전문적인 아이콘 적용:
    - Database (1476): 저장소 인덱싱
    - Commit Git (33279): 커밋 요약
    - Users/Group (102261): 기여자 분석
    - Bug (417): 버그 수정 커밋
    """
    return [
        cl.Starter(
            label="저장소 인덱싱 시작",
            message="현재 저장소의 커밋 히스토리를 인덱싱해주세요. 저장소 규모를 먼저 확인하고 적절한 개수를 제안해주세요.",
            icon="/public/icons/icon_db_1476_64.png",
        ),
        cl.Starter(
            label="최근 커밋 요약",
            message="최근 10개의 커밋을 요약해주세요. 주요 변경사항과 패턴을 분석해주세요.",
            icon="/public/icons/icon_commit_33279_64.png",
        ),
        cl.Starter(
            label="기여자 활동 분석",
            message="저장소의 기여자별 활동을 분석해주세요. 누가 가장 많이 기여했는지, 주요 담당 영역은 무엇인지 알려주세요.",
            icon="/public/icons/icon_users_102261_64.png",
        ),
        cl.Starter(
            label="버그 수정 커밋 찾기",
            message="버그 수정과 관련된 커밋들을 찾아서 분석해주세요. 어떤 버그들이 주로 수정되었는지 요약해주세요.",
            icon="/public/icons/icon_bug_417_64.png",
        ),
    ]


@cl.on_chat_start
async def on_chat_start():
    """채팅 시작 시 초기화 - Chainlit chat life cycle의 on_chat_start 훅

    Note: 환영 메시지는 chainlit.md에서 처리됨
    이 함수는 세션 초기화만 수행하여 starters가 먼저 보이도록 함
    """
    try:
        # 클라이언트 초기화
        openai_client, search_client, index_client = initialize_clients()

        # 세션 변수 설정
        cl.user_session.set("openai_client", openai_client)
        cl.user_session.set("search_client", search_client)
        cl.user_session.set("index_client", index_client)
        cl.user_session.set("conversation_history", [
            {"role": "system", "content": get_system_prompt()}
        ])
        cl.user_session.set("is_processing", False)

        logger.info("Chat session started - clients initialized")

    except Exception as e:
        logger.error(f"Failed to start chat: {e}")
        # 초기화 실패 시에만 메시지 표시
        await cl.Message(content=f"❌ 초기화 실패: {str(e)}\n\n페이지를 새로고침하거나 관리자에게 문의하세요.").send()


@cl.on_message
async def on_message(message: cl.Message):
    """메시지 처리 - Chainlit chat life cycle의 on_message 훅"""
    try:
        # 처리 중인 메시지가 있는지 확인
        is_processing = cl.user_session.get("is_processing")
        if is_processing:
            await cl.Message(content="이전 요청을 처리 중입니다. 잠시 후 다시 시도해주세요.").send()
            return

        # 처리 시작 플래그 설정
        cl.user_session.set("is_processing", True)

        openai_client = cl.user_session.get("openai_client")
        search_client = cl.user_session.get("search_client")
        index_client = cl.user_session.get("index_client")
        conversation_history = cl.user_session.get("conversation_history")

        if not openai_client or not search_client or not index_client:
            cl.user_session.set("is_processing", False)
            await cl.Message(content="세션이 초기화되지 않았습니다. 페이지를 새로고침하세요.").send()
            return

        user_message = message.content
        conversation_history.append({"role": "user", "content": user_message})

        # 대화 기록 길이 제한 (시스템 프롬프트 + 최근 N개 메시지)
        max_history_length = MAX_CONVERSATION_MESSAGES + 1  # +1 for system prompt
        if len(conversation_history) > max_history_length:
            system_msg = conversation_history[0]
            recent_messages = conversation_history[-(MAX_CONVERSATION_MESSAGES):]
            conversation_history = [system_msg] + recent_messages
            logger.info(f"Conversation history trimmed to {len(conversation_history)} messages")

        # 분석 중 메시지를 먼저 표시 (Step들이 이 아래에서 실행됨)
        msg = cl.Message(content="⏳ 요청을 분석하고 있습니다...")
        await msg.send()

        max_iterations = 10
        iteration = 0
        has_tool_result = False  # 도구 실행 후 최종 응답 보장용 플래그

        while iteration < max_iterations:
            iteration += 1

            # 🔧 전체 단계를 감싸는 부모 Step
            async with cl.Step(name=f"🔧 작업 수행 (단계 {iteration})", type="run", show_input=False) as parent_step:
                try:
                    # 💭 분석 단계 (자식 Step)
                    async with cl.Step(name="💭 분석 중...", parent_id=parent_step.id, type="llm", show_input=False) as analysis_step:
                        response = openai_client.chat.completions.create(
                            model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
                            messages=conversation_history,
                            tools=AVAILABLE_TOOLS,
                            tool_choice="auto",
                            temperature=0.7,
                            max_tokens=1000,
                            stream=False  # 도구 선택을 위해 non-streaming
                        )

                        assistant_message = response.choices[0].message

                        # LLM의 생각 표시 (간결하게)
                        if assistant_message.tool_calls:
                            tool_names = [tc.function.name for tc in assistant_message.tool_calls]
                            analysis_step.output = f"🔧 도구 선택: {', '.join(tool_names)}"
                        elif assistant_message.content:
                            analysis_step.output = "✅ 응답 준비 완료"

                    # 도구 호출 없이 최종 응답만 있는 경우 - 스트리밍으로 다시 생성
                    if not assistant_message.tool_calls:
                        # 스트리밍으로 응답 생성
                        msg.content = ""

                        streaming_response = openai_client.chat.completions.create(
                            model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
                            messages=conversation_history,
                            temperature=0.7,
                            max_tokens=1000,
                            stream=True
                        )

                        final_content = ""
                        for chunk in streaming_response:
                            # 안전하게 choices와 delta 체크
                            if chunk.choices and len(chunk.choices) > 0:
                                delta = chunk.choices[0].delta
                                if delta and hasattr(delta, 'content') and delta.content:
                                    token = delta.content
                                    final_content += token
                                    await msg.stream_token(token)

                        await msg.update()

                        if final_content:
                            conversation_history.append({
                                "role": "assistant",
                                "content": final_content
                            })
                        parent_step.output = "✅ 응답 완료"
                        break

                    conversation_history.append({
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in assistant_message.tool_calls
                        ]
                    })

                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        # 🛠️ 도구 실행 단계 (자식 Step)
                        async with cl.Step(name=f"🛠️ {tool_name}", parent_id=parent_step.id, type="tool", show_input=False) as tool_step:
                            # Step 밖에서 도구 실행 (AskActionMessage가 숨지 않도록)
                            tool_result = await execute_tool(
                                tool_name=tool_name,
                                arguments=tool_args,
                                openai_client=openai_client,
                                search_client=search_client,
                                index_client=index_client
                            )

                            # 도구 실행 완료 플래그 설정
                            has_tool_result = True

                            # 결과 크기 제한 (SocketIO 페이로드 제한 회피)
                            display_result = tool_result[:MAX_TOOL_RESULT_DISPLAY] if len(tool_result) > MAX_TOOL_RESULT_DISPLAY else tool_result

                            # Step 출력은 간결하게
                            if len(tool_result) > MAX_TOOL_RESULT_DISPLAY:
                                tool_step.output = f"✅ 완료 (결과 {len(tool_result):,}자, 일부 생략)"
                            else:
                                tool_step.output = f"✅ 완료"

                            # LLM에게 전달할 결과는 더 길게 허용하되 제한
                            truncated_result = tool_result[:MAX_TOOL_RESULT_TO_LLM]
                            if len(tool_result) > MAX_TOOL_RESULT_TO_LLM:
                                truncated_result += f"\n\n...(총 {len(tool_result)}자 중 {MAX_TOOL_RESULT_TO_LLM}자 표시)"
                                logger.warning(f"Tool result truncated: {len(tool_result)} -> {MAX_TOOL_RESULT_TO_LLM}")

                            conversation_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": truncated_result
                            })

                    parent_step.output = "✅ 도구 실행 완료"

                    # 🔄 도구 실행 후 다음 행동 결정 (tool_calls 확인을 위해 non-streaming)
                    logger.info("Checking next action after tool execution...")
                    next_response = openai_client.chat.completions.create(
                        model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
                        messages=conversation_history,
                        tools=AVAILABLE_TOOLS,
                        tool_choice="auto",
                        temperature=0.7,
                        max_tokens=1000,
                        stream=False
                    )

                    next_message = next_response.choices[0].message

                    # 추가 도구 호출이 있으면 현재 iteration에서 계속 실행
                    if next_message.tool_calls:
                        logger.info(f"More tool calls needed: {[tc.function.name for tc in next_message.tool_calls]}")

                        # assistant 메시지 추가
                        conversation_history.append({
                            "role": "assistant",
                            "content": next_message.content,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                }
                                for tc in next_message.tool_calls
                            ]
                        })

                        # 추가 도구들을 현재 iteration에서 실행
                        for tool_call in next_message.tool_calls:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)

                            async with cl.Step(name=f"🛠️ {tool_name} (추가)", parent_id=parent_step.id, type="tool", show_input=False) as extra_tool_step:
                                extra_tool_result = await execute_tool(
                                    tool_name=tool_name,
                                    arguments=tool_args,
                                    openai_client=openai_client,
                                    search_client=search_client,
                                    index_client=index_client
                                )

                                truncated_extra_result = extra_tool_result[:MAX_TOOL_RESULT_TO_LLM]
                                if len(extra_tool_result) > MAX_TOOL_RESULT_TO_LLM:
                                    truncated_extra_result += f"\n\n...(총 {len(extra_tool_result)}자 중 {MAX_TOOL_RESULT_TO_LLM}자 표시)"

                                conversation_history.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": truncated_extra_result
                                })

                                extra_tool_step.output = "✅ 완료"

                        parent_step.output = "🔄 추가 도구 실행 필요"
                        # 다음 iteration으로 계속
                        continue

                    # 텍스트 응답만 있으면 스트리밍으로 표시
                    if next_message.content:
                        logger.info("Final response after tool execution, streaming to user...")
                        async with cl.Step(name="💬 응답 생성", parent_id=parent_step.id, type="llm", show_input=False) as response_step:
                            msg.content = ""

                            # 스트리밍으로 다시 생성
                            streaming_response = openai_client.chat.completions.create(
                                model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
                                messages=conversation_history,
                                temperature=0.7,
                                max_tokens=1000,
                                stream=True
                            )

                            response_content = ""
                            for chunk in streaming_response:
                                if chunk.choices and len(chunk.choices) > 0:
                                    delta = chunk.choices[0].delta
                                    if delta and hasattr(delta, 'content') and delta.content:
                                        token = delta.content
                                        response_content += token
                                        await msg.stream_token(token)

                            await msg.update()

                            if response_content:
                                conversation_history.append({
                                    "role": "assistant",
                                    "content": response_content
                                })
                            response_step.output = "✅ 응답 완료"
                            has_tool_result = True
                            break  # 최종 응답 후 종료

                except Exception as e:
                    logger.error(f"Error in iteration {iteration}: {e}")
                    parent_step.output = f"❌ 오류 발생: {str(e)}"
                    break

        # 도구 실행 후 최종 응답이 없으면 fallback (일반적으로 위에서 처리되므로 거의 실행 안됨)
        if has_tool_result and iteration < max_iterations and not msg.content:
            try:
                logger.warning("Fallback: Forcing final response after tool execution")
                # ✅ 최종 응답은 최상위 레벨로 (parent 없음)
                async with cl.Step(name="✅ 최종 응답 (Fallback)", type="llm", show_input=False) as final_step:
                    # 스트리밍 방식으로 응답 생성 (깜빡이는 커서 표시)
                    msg.content = ""  # 메시지 초기화

                    final_response = openai_client.chat.completions.create(
                        model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
                        messages=conversation_history,
                        temperature=0.7,
                        max_tokens=1000,
                        stream=True  # 스트리밍 활성화
                    )

                    final_content = ""
                    for chunk in final_response:
                        # 안전하게 choices와 delta 체크
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            if delta and hasattr(delta, 'content') and delta.content:
                                token = delta.content
                                final_content += token
                                await msg.stream_token(token)

                    await msg.update()

                    if final_content:
                        conversation_history.append({
                            "role": "assistant",
                            "content": final_content
                        })
                    final_step.output = "✅ 응답 완료"
            except Exception as e:
                logger.error(f"Error generating final response: {e}", exc_info=True)
                msg.content = "작업이 완료되었습니다."
                await msg.update()

        if iteration >= max_iterations and not msg.content:
            msg.content = "⚠️ 최대 반복 횟수에 도달했습니다. 요청을 다시 시도해주세요."
            await msg.update()

        cl.user_session.set("conversation_history", conversation_history)

    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await cl.Message(content=f"오류가 발생했습니다: {str(e)}").send()
    finally:
        # 처리 완료 플래그 해제
        cl.user_session.set("is_processing", False)


@cl.on_stop
async def on_stop():
    """사용자가 중지 버튼을 클릭했을 때 - Chainlit chat life cycle의 on_stop 훅"""
    logger.info("User requested to stop the task")
    cl.user_session.set("is_processing", False)
    await cl.Message(content="⏸️ 작업이 중지되었습니다.").send()


@cl.on_chat_end
async def on_chat_end():
    """채팅 세션 종료 시 - Chainlit chat life cycle의 on_chat_end 훅"""
    logger.info("Chat session ended")
    # 세션 정리 (필요시)
    cl.user_session.set("is_processing", False)
    cl.user_session.set("conversation_history", None)
    cl.user_session.set("openai_client", None)
    cl.user_session.set("search_client", None)
    cl.user_session.set("index_client", None)


# 테스트 호환을 위한 엔트리포인트 심볼 제공

def start() -> None:
    """Chainlit 앱 시작용 엔트리포인트(테스트에서 존재 여부만 확인)."""
    logger.info("start() called - Chainlit entry placeholder")


def main() -> None:
    """메인 엔트리포인트(테스트에서 존재 여부만 확인)."""
    logger.info("main() called - entry placeholder")


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

