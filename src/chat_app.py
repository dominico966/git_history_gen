"""
Chainlit 기반 대화형 Git 히스토리 분석 채팅 앱
프롬프트는 구조화된 객체로 관리하며 여러 줄 문자열(''' or \"\"\") 사용 금지
"""

import json
import logging
import os
import sys
from pathlib import Path

import chainlit as cl
from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 도구 레지스트리와 실행기(분리된 모듈)
from src.tool_executor import initialize_clients, execute_tool

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
    "5. 규모별: ~500(기본), 500~1000(skip_offset), 1000+(날짜범위)",
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
    "- **절대 limit 없이 호출하지 말 것** (기본값 500개만 처리됨)",
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
    "# ⚠️ commit_sha 사용 규칙",
    "- **search_commits 결과의 commit_id는 실제 커밋 SHA 해시입니다**",
    "- get_commit_diff, read_file_from_commit 등을 호출할 때:",
    "  ✅ DO: commit_id 값을 그대로 사용 (예: 'a1b2c3d4e5f6')",
    "  ❌ DON'T: 커밋 메시지를 사용 (예: 'feat: 새 기능')",
    "- 예시:",
    "  search_commits → commit_id: 'abc123def456'",
    "  get_commit_diff(commit_sha='abc123def456') ✅",
    "  get_commit_diff(commit_sha='feat: 새 기능') ❌",
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

# 도구 등록은 별도 모듈로 분리되어 있습니다: `src.tool_registry` (도구 레지스트리 및 AVAILABLE_TOOLS)
from src.tool_registry import AVAILABLE_TOOLS


# Chainlit 페이지 메타데이터 is intentionally not set at import time to avoid
# accessing Chainlit registry during plain imports. It can be configured in
# runtime hooks if desired.



# 스타터 제안 (앱 시작 시 표시)
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
                        "content": assistant_message.content or "",
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
                            tool_result = await execute_tool(
                                tool_name=tool_name,
                                arguments=tool_args,
                                openai_client=openai_client,
                                search_client=search_client,
                                index_client=index_client
                            )

                            # 도구 실행 완료 플래그 설정
                            has_tool_result = True

                            # Step 출력은 간결하게
                            if len(tool_result) > MAX_TOOL_RESULT_DISPLAY:
                                tool_step.output = f"✅ 완료 (결과 {len(tool_result):,}자)"
                            else:
                                tool_step.output = f"✅ 완료"

                            # LLM에게 전달할 결과는 제한
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
                            "content": next_message.content or "",
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

                    # 텍스트 응답이 있으면 conversation_history에 추가하고 루프 종료
                    if next_message.content:
                        logger.info("Final response ready, adding to history")
                        conversation_history.append({
                            "role": "assistant",
                            "content": next_message.content
                        })
                        parent_step.output = "✅ 완료"
                        has_tool_result = False  # 이미 응답이 있으므로 밖에서 생성하지 않음

                        # msg에 내용 표시
                        msg.content = next_message.content
                        await msg.update()
                        break  # 루프 종료

                except Exception as e:
                    logger.error(f"Error in iteration {iteration}: {e}")
                    parent_step.output = f"❌ 오류 발생: {str(e)}"
                    break

        # 최대 반복 횟수 도달 시에만 경고 메시지
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




