# Chainlit Chat App 사용 가이드

## 개요
`src/chat_app.py`는 Chainlit 기반의 대화형 Git 저장소 분석 애플리케이션입니다.

## 주요 기능

### 1. 이중 히스토리 관리
- **conversation_history**: 화면에 표시되는 사용자-어시스턴트 대화만 저장
- **toolcall_judge_history**: 시스템 프롬프트 + 도구 호출 판단 및 이력 포함

### 2. 도구 시스템
다음 5가지 도구를 LLM Function Calling으로 제공:

- **index_repository**: Git 저장소를 Azure AI Search에 인덱싱
- **get_commit_summary**: 최근 커밋을 LLM으로 분석하여 요약
- **search_commits**: 자연어로 커밋 검색 (하이브리드 검색)
- **analyze_contributors**: 기여자별 통계 및 평가
- **find_bug_commits**: 버그 수정 관련 커밋 추출

### 3. Step 표시
모든 도구 실행 시 Chainlit Step을 사용하여 중간 작업 진행 상황을 표시합니다.

## 실행 방법

### 1. 환경 변수 설정
`.env` 파일에 다음 변수들을 설정:
```
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_MODEL=gpt-4-turbo
AZURE_SEARCH_ENDPOINT=your_search_endpoint
AZURE_SEARCH_API_KEY=your_search_key
AZURE_SEARCH_INDEX_NAME=git-commits
```

### 2. Chainlit 실행
```powershell
chainlit run src/chat_app.py -w
```

`-w` 옵션은 파일 변경 시 자동 재시작을 활성화합니다.

### 3. 브라우저에서 접속
기본적으로 `http://localhost:8000`에서 실행됩니다.

## 사용 예시

### 저장소 인덱싱
```
현재 디렉토리의 최근 100개 커밋을 인덱싱해줘
```

### 커밋 요약
```
최근 50개 커밋을 요약해줘
```

### 커밋 검색
```
로그인 기능 관련 커밋 찾아줘
```

### 기여자 분석
```
누가 가장 많이 기여했는지 분석해줘
```

### 버그 커밋 찾기
```
버그 수정 커밋들을 찾아줘
```

## 아키텍처 특징

### 대화 흐름
1. 사용자 메시지 입력
2. `toolcall_judge_history`로 LLM에게 전달
3. LLM이 도구 호출 필요성 판단
4. 필요시 도구 실행 (Step 표시)
5. 도구 결과를 기반으로 최종 응답 생성
6. `conversation_history`에 사용자-어시스턴트 대화만 저장

### 시스템 프롬프트
`SYSTEM_PROMPT`에서 도구 사용 방법과 대화 가이드라인을 LLM에게 제공합니다.

### 도구 스키마
`create_tools_schema()`에서 OpenAI Function Calling 형식의 도구 스키마를 정의합니다.

### 에러 처리
- 초기화 실패 시 상세한 오류 메시지 표시
- 도구 실행 실패 시 사용자에게 친절한 오류 안내
- 모든 예외는 로깅되어 디버깅 가능

## 테스트
```powershell
python -m pytest tests/test_chat_app.py -v
```

모든 테스트가 통과함을 확인했습니다.

## 개발 노트

### 타입 힌트
OpenAI SDK의 타입 정의와 Python dict 간 변환을 위해 `cast()`를 사용합니다.
타입 체커 경고가 있을 수 있으나, 런타임에는 정상 동작합니다.

### 비동기 처리
Chainlit은 비동기 기반이므로, 모든 핸들러 함수는 `async def`로 정의됩니다.

### 세션 관리
`cl.user_session`을 통해 사용자별 대화 히스토리를 관리합니다.

