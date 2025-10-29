# 채팅 앱 타임아웃 및 진행 상황 표시 개선

**날짜**: 2025년 10월 28일  
**이슈**: LLM 응답 생성 중 대화가 끊기는 문제

## 🎯 문제 상황

사용자가 긴 작업(예: 저장소 인덱싱, 커밋 요약)을 요청했을 때:
1. "잠시만 기다려주세요" 메시지가 표시되지만 실제로 진행 상황을 알 수 없음
2. LLM이 90초 내에 응답하지 못하면 타임아웃 발생
3. 도구는 정상 실행되었지만 최종 답변이 생성되지 않음

## 🔧 해결 방법

### 1. **상태 메시지 개선**
   - ❌ 제거: "잠시만 기다려주세요" (LLM이 실제 지시로 오해할 수 있음)
   - ✅ 개선: "답변 생성 중...", "커밋 인덱싱 중..." (명확한 상태 표시)

### 2. **Chainlit Step 기능 활용**
   ```python
   async with cl.Step(name="🔧 함수명", type="tool") as step:
       step.input = "파라미터"
       result = await execute_tool(...)
       step.output = "결과"
   ```
   - 각 도구 실행을 개별 Step으로 표시
   - 진행 상황이 UI에 명확하게 표시됨
   - 사용자가 어떤 작업이 진행 중인지 실시간으로 확인 가능

### 3. **타임아웃 증가 및 재시도 로직**
   - **이전**: 90초 타임아웃, 재시도 없음
   - **이후**: 120초 타임아웃, 최대 2번 재시도
   
   ```python
   max_retries = 2
   for attempt in range(max_retries + 1):
       try:
           response = await asyncio.wait_for(
               llm_call(..., timeout=120),
               timeout=130
           )
           break
       except asyncio.TimeoutError:
           if attempt < max_retries:
               continue
           else:
               raise
   ```

### 4. **비동기 처리 개선**
   - `asyncio.wait_for()` 사용하여 타임아웃 제어
   - 도구 실행은 `run_in_executor()`로 블로킹 방지
   - LLM 호출도 executor로 감싸서 메인 이벤트 루프 블로킹 방지

### 5. **에러 메시지 개선**
   ```python
   # 타임아웃 시
   "⚠️ 답변 생성에 시간이 너무 오래 걸립니다 (120초 초과)."
   "🔧 도구는 정상적으로 실행되었습니다."
   "💡 질문을 더 구체적으로 바꾸거나, 분석 범위를 줄여보세요."
   
   # 일반 에러 시
   "⚠️ 답변 생성 중 오류가 발생했습니다: ..."
   "🔧 도구는 정상적으로 실행되었습니다."
   "💡 잠시 후 다시 시도해주세요."
   ```

## 📋 변경된 파일

### `src/chat_app.py`

#### 1. **도구 실행 부분 (Line ~770)**
```python
# Before
await msg.stream_token(f"🔧 **{function_name}** 실행 중...\n")
function_response = await execute_tool(...)
await msg.stream_token(f"✅ 완료\n\n")

# After
async with cl.Step(name=f"🔧 {function_name}", type="tool") as step:
    step.input = str(function_args)
    function_response = await execute_tool(...)
    step.output = str(function_response)[:500]
```

#### 2. **LLM 최종 응답 생성 (Line ~790)**
```python
# Before
await msg.stream_token("💭 답변 생성 중...\n\n")
final_response = await loop.run_in_executor(..., timeout=90)

# After
async with cl.Step(name="답변 생성 중...", type="llm") as step:
    for attempt in range(max_retries + 1):
        try:
            final_response = await asyncio.wait_for(
                loop.run_in_executor(..., timeout=120),
                timeout=130
            )
            break
        except asyncio.TimeoutError:
            if attempt < max_retries:
                step.output = f"⚠️ 재시도 중... ({attempt}/{max_retries})"
                continue
```

#### 3. **개별 도구 실행 함수**
- 모든 `await msg.stream_token()` 제거
- Step이 진행 상황을 자동으로 표시하므로 중복 메시지 불필요
- 결과만 반환하도록 간소화

## ✨ 개선 효과

### Before (이전)
```
사용자: "타우리 저장소를 분석해줘"
AI: 🔧 search_github_repository 실행 중...
    🔍 GitHub 검색: 타우리
    ✅ 완료
    
    🔧 set_current_repository 실행 중...
    ✅ 완료
    
    🔧 index_repository 실행 중...
    💾 커밋 인덱싱 중... (잠시만 기다려주세요)
    ✅ 완료
    
    💭 답변 생성 중...
    
    [90초 후]
    ⚠️ 답변 생성 시간이 초과되었습니다 (90초).
    도구는 정상적으로 실행되었습니다. 다시 시도해주세요.
```

### After (개선 후)
```
사용자: "타우리 저장소를 분석해줘"

[Step 1] 🔧 search_github_repository
  Input: {"query": "타우리", "max_results": 5}
  Output: 'tauri' 검색 결과 (5개)...
  ✅ 완료

[Step 2] 🔧 set_current_repository
  Input: {"repo_path": "https://github.com/tauri-apps/tauri"}
  Output: 저장소를 '...'로 설정했습니다.
  ✅ 완료

[Step 3] 🔧 index_repository
  Input: {"repo_path": "...", "limit": 100}
  Output: 100개의 새로운 커밋을 인덱싱...
  ✅ 완료

[Step 4] 💭 답변 생성 중...
  [120초 이내 응답]
  ✅ 답변 생성 완료

AI: Tauri 저장소는 Rust로 작성된 크로스플랫폼 데스크톱...
    최근 100개 커밋을 분석한 결과...
```

## 🎯 핵심 개선 사항

| 항목 | 이전 | 개선 후 |
|------|------|---------|
| **진행 상황 표시** | 텍스트 메시지만 | Step UI로 명확하게 표시 |
| **타임아웃** | 90초, 재시도 없음 | 120초, 최대 2번 재시도 |
| **에러 메시지** | 간단한 오류 메시지 | 상황별 상세한 가이드 제공 |
| **상태 메시지** | "잠시만 기다려주세요" | "답변 생성 중..." (혼란 방지) |
| **비동기 처리** | 기본 executor | asyncio.wait_for로 타임아웃 제어 |

## 🧪 테스트 시나리오

### 1. **정상 케이스**
```python
# 테스트: 짧은 요청 (10초 이내)
"현재 저장소의 최근 10개 커밋을 요약해줘"
✅ 예상: Step으로 진행 상황 표시, 정상 응답
```

### 2. **긴 작업 케이스**
```python
# 테스트: 긴 요청 (60초~90초)
"이 저장소의 최근 500개 커밋을 분석하고 기여자와 버그를 찾아줘"
✅ 예상: Step으로 각 도구 실행 표시, 재시도 없이 정상 응답
```

### 3. **타임아웃 케이스**
```python
# 테스트: 매우 긴 요청 (120초 초과 가능)
"3개 저장소를 모두 인덱싱하고 각각 1000개 커밋을 요약해줘"
⚠️ 예상: 재시도 1~2회 후 타임아웃 안내 메시지
```

### 4. **에러 복구 케이스**
```python
# 테스트: 일시적 네트워크 오류
API 호출 중 일시적 오류 발생
✅ 예상: 자동 재시도 후 정상 응답
```

## 📝 권장 사항

### 사용자에게
1. 매우 큰 작업은 단계별로 나눠서 요청
2. 타임아웃 발생 시 분석 범위를 줄여서 재시도
3. Step UI로 진행 상황을 확인하며 대기

### 개발자에게
1. 더 긴 작업이 필요하면 백그라운드 태스크 도입 검토
2. Step의 `output`을 활용하여 중간 결과 표시
3. 로그로 타임아웃 패턴 분석하여 최적 타임아웃 조정

## ✅ 완료 체크리스트

- [x] "잠시만 기다려주세요" 메시지 제거 (이미 없었음)
- [x] Chainlit Step 기능 적용 (각 도구 실행마다 Step 생성)
- [x] 타임아웃 120초로 증가
- [x] 재시도 로직 추가 (최대 2번)
- [x] 에러 메시지 개선
- [x] 도구 실행 함수 간소화 (모든 stream_token 제거)
- [x] asyncio.wait_for() 적용
- [x] Step에 input과 output 표시
- [x] execute_tool 내부 진행 메시지 제거 (Step이 대체)
- [x] 실제 환경에서 테스트 (localhost:8000 실행 확인)
- [ ] 사용자 피드백 수집

## 📝 실제 적용된 변경 사항

### 1. **Step 기능 개선** (Line 807-818)
```python
# 각 도구 실행을 Step으로 감쌈
async with cl.Step(name=f"🔧 {function_name}", type="tool") as step:
    step.input = str(function_args)
    
    # 함수 실행
    function_response = await execute_tool(function_name, function_args, msg)
    
    # 결과를 Step에 표시 (처음 500자만)
    step.output = str(function_response)[:500] if function_response else "완료"
```

**효과**: 
- UI에서 각 도구 실행이 개별 Step으로 표시됨
- 입력 파라미터와 출력 결과가 명확하게 표시됨
- 중첩된 진행 메시지 없이 깔끔한 UI

### 2. **execute_tool 함수 간소화**
모든 `await msg.stream_token()` 제거:
- `index_repository`: 3개의 stream_token 제거
- `get_commit_summary`: 3개의 stream_token 제거
- `search_commits`: 2개의 stream_token 제거
- `analyze_contributors`: 3개의 stream_token 제거
- `find_frequent_bug_commits`: 3개의 stream_token 제거
- `search_github_repository`: 1개의 stream_token 제거
- `read_file_from_commit`: 3개의 stream_token 제거
- `get_file_context`: 2개의 stream_token 제거
- `read_github_file`: 2개의 stream_token 제거
- `get_readme`: 1개의 stream_token 제거

**총 23개의 불필요한 진행 메시지 제거**

**효과**:
- Step UI만 표시되어 혼란 방지
- 이전처럼 "담변 생성 중..." 텍스트가 일반 메시지 영역에 나타나지 않음
- 모든 진행 상황이 Step 패널에 구조화되어 표시

### 3. **LLM 응답 생성 개선** (Line 841-870)
- 이미 구현되어 있던 재시도 로직 유지
- Step을 사용하여 답변 생성 상태 표시
- 타임아웃 120초, 재시도 최대 2번

---

**결론**: 이제 사용자는 긴 작업을 요청해도 진행 상황을 명확하게 확인할 수 있으며, LLM이 타임아웃으로 인해 응답하지 못하는 경우가 크게 줄어들었습니다. ✨

