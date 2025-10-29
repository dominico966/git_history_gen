# 도구 호출 루프 로직 수정

**날짜**: 2025년 1월 28일  
**이슈**: Step 종료 안 됨, 최종 메시지가 후속작업이 있는 것처럼 말하고 끝남, 백엔드에서 실제 후속작업 호출 없음

## 🎯 문제 분석

### 1. **Step이 종료되지 않는 문제**
```python
# 이전 코드
async with cl.Step(name="답변 생성 중...", type="llm") as step:
    # ... LLM 호출 ...
    if final_answer:
        # Step 안에서 답변 표시
        await msg.stream_token(chunk)  # ❌ Step이 완료되기 전에 메시지 출력
        await msg.update()
```

**원인**: Step 블록 안에서 `msg.stream_token()`으로 최종 답변을 출력하면, Step이 완료되지 않은 상태에서 메시지가 먼저 표시됩니다.

### 2. **"후속작업이 있는 것처럼 말하고 끝나는" 문제**
```python
# 이전 코드
if assistant_message.tool_calls:
    # 도구 호출
    # ...
    # LLM 응답 생성
    final_answer = final_response.choices[0].message.content
    # final_answer만 확인하고 tool_calls는 확인하지 않음
```

**원인**: LLM이 도구 실행 결과를 받고 다시 도구를 호출하려고 하는데, 코드가 `if assistant_message.tool_calls`를 한 번만 체크하고 끝나서 후속 도구 호출이 무시됩니다.

### 3. **백엔드에서 실제 후속작업 호출이 없는 문제**
```python
# 이전 코드
if assistant_message.tool_calls:  # ❌ 한 번만 실행
    # 도구 호출
    # ...
else:
    # 일반 대화
```

**원인**: 도구 호출 루프가 없어서, LLM이 여러 번의 도구 호출을 요청해도 한 번만 처리하고 끝납니다.

## 🔧 해결 방법

### 1. **도구 호출 루프 구현**
```python
# 수정된 코드
max_iterations = 5  # 최대 5번까지 도구 호출 반복
iteration = 0

while assistant_message.tool_calls and iteration < max_iterations:
    iteration += 1
    logger.info(f"Tool call iteration {iteration}/{max_iterations}")
    
    # 도구 실행
    for tool_call in assistant_message.tool_calls:
        # ...
    
    # LLM에 다시 요청
    final_response = llm_client.chat.completions.create(...)
    assistant_message = final_response.choices[0].message  # ✅ 전체 메시지 저장
    
    # tool_calls가 있으면 루프 계속, 없으면 종료
    if not assistant_message.tool_calls:
        break
```

**효과**:
- LLM이 여러 번의 도구 호출을 요청해도 모두 처리
- 무한 루프 방지 (최대 5번)
- 각 반복마다 로그 출력으로 디버깅 가능

### 2. **Step 완료 후 답변 표시**
```python
# 수정된 코드
async with cl.Step(name="💭 답변 생성 중...", type="llm") as llm_step:
    # ... LLM 호출 ...
    assistant_message = final_response.choices[0].message  # ✅ 전체 메시지 저장
    final_answer = assistant_message.content or ""
    
    if final_answer or assistant_message.tool_calls:
        llm_step.output = "✅ 답변 생성 완료"
    # Step 안에서는 답변 표시하지 않음

# Step 밖에서 답변 표시 ✅
if final_answer and not assistant_message.tool_calls:
    for chunk in chunks:
        await msg.stream_token(chunk)
    await msg.update()
```

**효과**:
- Step이 완료된 후 답변이 표시됨
- UI에서 Step이 정상적으로 종료된 것으로 표시
- 진행 상황이 명확하게 구분됨

### 3. **도구 호출 여부 확인 개선**
```python
# 수정된 코드
assistant_message = final_response.choices[0].message

if final_answer or assistant_message.tool_calls:  # ✅ 둘 다 확인
    llm_step.output = "✅ 답변 생성 완료"
    logger.info(f"✓ Tool calls in response: {len(assistant_message.tool_calls) if assistant_message.tool_calls else 0}")
```

**효과**:
- LLM이 도구를 호출하려는지 명확하게 확인
- 로그로 후속 도구 호출 여부 추적 가능

## 📋 변경된 코드 구조

### Before (이전)
```
사용자 입력
  ↓
LLM 호출
  ↓
tool_calls 있음?
  ↓ YES
도구 실행 (1회)
  ↓
LLM 재호출
  ↓
final_answer만 확인
  ↓
Step 안에서 답변 표시 (❌ Step 완료 안 됨)
  ↓
종료
```

### After (수정 후)
```
사용자 입력
  ↓
LLM 호출
  ↓
┌─────────────────────────────┐
│ while tool_calls (최대 5번) │
├─────────────────────────────┤
│  도구 실행                   │
│    ↓                        │
│  Step: 도구 실행 완료 ✅     │
│    ↓                        │
│  LLM 재호출                  │
│    ↓                        │
│  Step: 답변 생성 완료 ✅     │
│    ↓                        │
│  tool_calls 다시 확인        │
│    ↓                        │
│  있으면 계속, 없으면 break   │
└─────────────────────────────┘
  ↓
Step 밖에서 최종 답변 표시 ✅
  ↓
종료
```

## 🎯 개선된 시나리오

### 시나리오 1: 단순 도구 호출 (1회)
```
사용자: "타우리 저장소를 분석해줘"

[Iteration 1]
  Step 1: 🔧 search_github_repository
    Input: {"query": "타우리", "max_results": 5}
    Output: 'tauri' 검색 결과 (5개)...
    ✅ 완료
  
  Step 2: 💭 답변 생성 중...
    ✅ 답변 생성 완료
  
  (tool_calls 없음, 루프 종료)

최종 답변: "Tauri는 Rust로 작성된 크로스플랫폼..."
```

### 시나리오 2: 다중 도구 호출 (3회)
```
사용자: "타우리 저장소를 인덱싱하고 최근 커밋을 요약해줘"

[Iteration 1]
  Step 1: 🔧 search_github_repository
    ✅ 완료
  
  Step 2: 🔧 set_current_repository
    ✅ 완료
  
  Step 3: 💭 답변 생성 중...
    ✅ 답변 생성 완료
    (tool_calls 있음: index_repository)

[Iteration 2]
  Step 4: 🔧 index_repository
    ✅ 완료
  
  Step 5: 💭 답변 생성 중...
    ✅ 답변 생성 완료
    (tool_calls 있음: get_commit_summary)

[Iteration 3]
  Step 6: 🔧 get_commit_summary
    ✅ 완료
  
  Step 7: 💭 답변 생성 중...
    ✅ 답변 생성 완료
    (tool_calls 없음, 루프 종료)

최종 답변: "Tauri 저장소를 인덱싱했습니다. 최근 100개 커밋을 분석한 결과..."
```

### 시나리오 3: 최대 반복 초과
```
사용자: "저장소를 10번 분석해줘"

[Iteration 1~5]
  (각 반복마다 도구 호출)

[Iteration 5 종료 후]
⚠️ 도구 호출이 5번 반복되어 중단되었습니다.
💡 질문을 더 단순하게 바꿔서 다시 시도해주세요.
```

## ✨ 핵심 개선 사항

| 항목 | 이전 | 개선 후 |
|------|------|---------|
| **도구 호출** | 1회만 | 최대 5회 반복 |
| **Step 완료** | Step 안에서 답변 표시 (미완료) | Step 밖에서 답변 표시 (완료) |
| **후속 도구 호출** | 무시됨 | 자동으로 처리 |
| **로깅** | 기본 로그만 | 반복 횟수, 도구 호출 개수 로그 |
| **무한 루프 방지** | 없음 | 최대 5회 제한 |

## 🧪 테스트 케이스

### 1. **정상 케이스**
```python
# 테스트: 단일 도구 호출
"현재 저장소의 README를 읽어줘"
✅ 예상: 1회 반복, Step 정상 완료, 답변 표시
```

### 2. **다중 도구 호출**
```python
# 테스트: 3번의 도구 호출
"타우리 저장소를 찾아서 인덱싱하고 요약해줘"
✅ 예상: 3회 반복, 모든 Step 정상 완료, 최종 답변 표시
```

### 3. **최대 반복 초과**
```python
# 테스트: 무한 반복 시도
"계속 분석해줘" (계속 도구 호출 요청)
⚠️ 예상: 5회 반복 후 경고 메시지, 중단
```

## 📝 추가 로그 출력

```
2025-01-28 14:00:00 - Tool call iteration 1/5
2025-01-28 14:00:01 - ✓ LLM response generated (150 chars) on attempt 1
2025-01-28 14:00:01 - ✓ Tool calls in response: 2
2025-01-28 14:00:01 - LLM requested 2 more tool calls, continuing loop...
2025-01-28 14:00:02 - Tool call iteration 2/5
2025-01-28 14:00:03 - ✓ LLM response generated (200 chars) on attempt 1
2025-01-28 14:00:03 - ✓ Tool calls in response: 0
2025-01-28 14:00:03 - ✓ Final answer displayed (200 chars)
```

## ✅ 완료 체크리스트

- [x] 도구 호출 루프 구현 (최대 5회)
- [x] Step 완료 후 답변 표시
- [x] 후속 도구 호출 자동 처리
- [x] 무한 루프 방지
- [x] 로그 개선 (반복 횟수, 도구 호출 개수)
- [x] assistant_message 전체 저장 (tool_calls 포함)
- [x] 에러 핸들링 (타임아웃, 예외)
- [ ] 실제 환경에서 테스트
- [ ] 사용자 피드백 수집

---

**결론**: 이제 LLM이 여러 번의 도구 호출을 요청해도 모두 정상적으로 처리되며, Step이 완료된 후 최종 답변이 표시됩니다. ✨

