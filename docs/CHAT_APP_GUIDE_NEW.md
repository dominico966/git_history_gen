# Chat App 실행 가이드

## 개요
`src/chat_app.py`는 Chainlit 기반 대화형 Git 히스토리 분석 챗봇입니다.

## 주요 특징
✅ **여러 줄 문자열 사용 금지** - 모든 프롬프트는 구조화된 리스트/딕셔너리로 관리
✅ **OpenAI Function Calling** - 8개 도구 자동 선택 및 실행
✅ **대화 컨텍스트 유지** - conversation_history로 이전 대화 참조
✅ **중간 과정 표시** - Chainlit Step으로 도구 실행 과정 시각화
✅ **비동기 처리** - 효율적인 리소스 활용

## 사용 가능한 도구

1. **get_commit_summary** - 최근 커밋 요약 및 분석
2. **search_commits** - 자연어로 커밋 검색
3. **analyze_contributors** - 기여자별 활동 분석
4. **find_bug_commits** - 버그 수정 커밋 찾기
5. **search_github_repo** - GitHub 저장소 검색
6. **read_file_from_commit** - 특정 커밋의 파일 읽기
7. **get_file_context** - 파일 변경 컨텍스트 및 diff
8. **get_readme** - 저장소 README 읽기

## 환경 설정

### 1. 환경 변수 설정
`.env` 파일에 다음 변수를 설정하세요:

```env
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_MODEL=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your_search_key
AZURE_SEARCH_INDEX_NAME=git-commits
```

### 2. 의존성 설치 확인
```powershell
uv sync
```

## 실행 방법

### 방법 1: 직접 실행
```powershell
chainlit run src/chat_app.py -w
```

### 방법 2: 포트 지정
```powershell
chainlit run src/chat_app.py -w --port 8000
```

### 방법 3: 디버그 모드
```powershell
$env:CHAINLIT_DEBUG="true"
chainlit run src/chat_app.py -w
```

## 테스트

### 기본 테스트 실행
```powershell
pytest tests/test_chat_app_basic.py -v -s
```

### 특정 테스트만 실행
```powershell
pytest tests/test_chat_app_basic.py::test_system_prompt_structure -v
```

## 사용 예시

### 예시 1: 최근 커밋 요약
```
사용자: C:\projects\myrepo 저장소의 최근 50개 커밋을 요약해줘
봇: [get_commit_summary 실행] → 분석 결과 제공
```

### 예시 2: 커밋 검색
```
사용자: API 관련 변경사항 찾아줘
봇: [search_commits 실행] → 관련 커밋 목록 제공
```

### 예시 3: 기여자 분석
```
사용자: 기여자들의 활동을 분석해줘
봇: [analyze_contributors 실행] → 통계 및 순위 제공
```

### 예시 4: GitHub 저장소 검색
```
사용자: Tauri 관련 저장소 찾아줘
봇: [search_github_repo 실행] → 상위 저장소 목록 제공
```

### 예시 5: 버그 커밋 찾기
```
사용자: 버그 수정 커밋들을 찾아줘
봇: [find_bug_commits 실행] → 버그 관련 커밋 목록
```

## 아키텍처

### 대화 흐름
```
사용자 메시지
  ↓
LLM 분석 (도구 필요 여부 판단)
  ↓
도구 호출 (필요시)
  ↓
결과 수집
  ↓
LLM 최종 응답 생성
  ↓
사용자에게 전달
```

### 프롬프트 관리 방식
```python
# ❌ 잘못된 방식 (여러 줄 문자열)
prompt = """
You are an assistant.
Use tools when needed.
"""

# ✅ 올바른 방식 (구조화된 리스트)
PROMPT_PARTS = [
    "You are an assistant.",
    "Use tools when needed."
]
PROMPT = " ".join(PROMPT_PARTS)

# ✅ 또는 딕셔너리
PROMPT_CONFIG = {
    "role": "system",
    "content": " ".join([
        "You are an assistant.",
        "Use tools when needed."
    ])
}
```

## 문제 해결

### 1. 포트 충돌
```powershell
# 다른 포트 사용
chainlit run src/chat_app.py -w --port 8001
```

### 2. 환경 변수 오류
```powershell
# .env 파일 확인
Get-Content .env
```

### 3. 클라이언트 초기화 실패
```powershell
# 연결 테스트
pytest tests/test_chat_app_basic.py::test_initialize_clients -v
```

### 4. 도구 실행 오류
로그 확인:
```python
# src/chat_app.py에서 로깅 레벨 조정
logging.basicConfig(level=logging.DEBUG)
```

## 코드 구조

```
src/chat_app.py
├── SYSTEM_PROMPT_PARTS      # 시스템 프롬프트 (리스트)
├── AVAILABLE_TOOLS          # 도구 정의 (OpenAI Function Calling)
├── initialize_clients()     # Azure 클라이언트 초기화
├── execute_tool()           # 도구 실행 로직
├── start()                  # 채팅 세션 시작 (@cl.on_chat_start)
└── main()                   # 메시지 처리 (@cl.on_message)
```

## 성능 최적화

1. **비동기 처리**: 모든 I/O 작업은 async/await 사용
2. **토큰 절약**: 도구 결과는 1000자로 제한 (필요시 전체 표시)
3. **반복 제한**: 최대 10회 반복으로 무한 루프 방지
4. **캐싱**: repo_cache를 통한 원격 저장소 캐싱

## 향후 개선 사항

- [ ] 스트리밍 응답 지원
- [ ] 대화 히스토리 저장/로드
- [ ] 다중 저장소 동시 분석
- [ ] 커스텀 도구 동적 추가
- [ ] 결과 시각화 (차트, 그래프)

## 참고 자료

- [Chainlit 문서](https://docs.chainlit.io/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)

