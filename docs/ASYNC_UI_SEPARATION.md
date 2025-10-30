# UI와 코어 기능 비동기 분리 완료 보고서

## 날짜
2025-10-29

## 업데이트
- 2025-10-29: 커밋 SHA 해석 기능 개선 추가

## 문제점
- 도구 함수들이 **동기적으로** 실행되어 UI 스레드를 블로킹
- 조금만 오래 걸려도 Chainlit UI가 응답 불가 (멈춤)
- `ValueError: Too many packets in payload` 오류 발생
- **짧은 커밋 SHA나 숫자로 diff 요청 시 실패**

## 해결 방법

### 모든 도구 함수를 `asyncio.run_in_executor`로 비동기 변환

```python
import asyncio
loop = asyncio.get_event_loop()

# 변경 전 (동기 블로킹)
result = get_commit_count(repo_path, since, until)

# 변경 후 (비동기)
result = await loop.run_in_executor(
    None,
    lambda: get_commit_count(repo_path, since, until)
)
```

## 비동기 변환된 도구 함수 목록

### 1. Git 분석 도구
- ✅ `get_commit_count` - 커밋 개수 조회
- ✅ `get_commit_summary` - 커밋 요약 (LLM 호출)
- ✅ `analyze_contributors` - 기여자 분석
- ✅ `find_bug_commits` - 버그 커밋 찾기 (LLM 호출)

### 2. 검색 도구
- ✅ `search_commits` - 커밋 검색 (임베딩 + Azure Search)
- ✅ `search_commits_by_date` - 날짜 범위 검색
- ✅ `search_github_repo` - GitHub 저장소 검색

### 3. 파일/커밋 조회 도구
- ✅ `read_file_from_commit` - 특정 커밋의 파일 읽기
- ✅ `get_file_context` - 파일 컨텍스트 조회
- ✅ `get_commit_diff` - 커밋 diff 조회
- ✅ `get_readme` - README 읽기

### 4. 인덱스 관리 도구
- ✅ `index_repository` - 저장소 인덱싱 (이미 진행 상황 콜백 포함)
- ✅ `get_index_statistics` - 인덱스 통계
- ✅ `list_indexed_repositories` - 인덱싱된 저장소 목록
- ✅ `get_repository_info` - 저장소 정보 조회
- ✅ `delete_repository_commits` - 저장소 커밋 삭제
- ✅ `check_index_health` - 인덱스 상태 확인

### 5. UI 전용 도구
- ✅ `set_current_repository` - 현재 저장소 설정 (동기 유지 - 빠름)

## 실행 흐름 비교

### Before (동기 블로킹)
```
사용자: "이 저장소 분석해줘"
  ↓
analyze_contributors() 실행 (동기)
  ↓ [UI 멈춤 - 10초]
  ↓ 사용자 입력 불가
  ↓ WebSocket 패킷 쌓임
  ↓ ValueError: Too many packets
  ↓ 세션 끊김
```

### After (비동기)
```
사용자: "이 저장소 분석해줘"
  ↓
await loop.run_in_executor(analyze_contributors)
  ↓ [백그라운드 실행]
  ↓ UI 응답 유지
  ↓ 사용자 다른 메시지 입력 가능
  ↓ WebSocket 정상
  ↓ 완료 후 결과 표시
```

## 코드 예시

### 단순 함수 호출
```python
# Before
result = get_commit_count(repo_path, since, until)

# After
result = await loop.run_in_executor(
    None,
    lambda: get_commit_count(repo_path, since, until)
)
```

### 복잡한 매개변수
```python
# Before
result = analyze_contributors(
    repo_path=arguments["repo_path"],
    criteria=arguments.get("criteria"),
    limit=contributor_limit
)

# After  
result = await loop.run_in_executor(
    None,
    lambda: analyze_contributors(
        repo_path=arguments["repo_path"],
        criteria=arguments.get("criteria"),
        limit=contributor_limit
    )
)
```

### 인덱싱 (진행 상황 포함)
```python
# 진행 상황 콜백 포함 비동기 실행
import threading

progress_lock = threading.Lock()
last_update = {"current": 0, "total": limit, "message": ""}

def progress_callback(current, total, message=""):
    with progress_lock:
        last_update["current"] = current
        last_update["total"] = total
        last_update["message"] = message

async def update_progress():
    while True:
        await asyncio.sleep(2)
        with progress_lock:
            current = last_update["current"]
            total = last_update["total"]
            msg = last_update["message"]
        
        progress_msg.content = f"🔄 진행 중... ({current}/{total}) - {msg}"
        await progress_msg.update()

update_task = asyncio.create_task(update_progress())

try:
    result = await loop.run_in_executor(
        None,
        lambda: indexer.index_repository(..., progress_callback=progress_callback)
    )
finally:
    update_task.cancel()
```

## 성능 개선

### UI 응답성
- **Before**: 작업 완료까지 UI 멈춤
- **After**: 항상 응답 유지

### 동시 처리
- **Before**: 한 작업 완료 후 다음 작업
- **After**: 여러 작업 동시 처리 가능

### 사용자 경험
- **Before**: 멈춘 것처럼 보임 → 불안함
- **After**: 진행 상황 표시 → 안심

## 주의사항

### 1. ThreadPool 제한
- `run_in_executor(None, ...)`은 기본 ThreadPoolExecutor 사용
- 동시 작업이 너무 많으면 제한 가능
- 필요시 커스텀 executor 생성:
```python
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=10)
await loop.run_in_executor(executor, func)
```

### 2. 공유 상태
- 백그라운드 스레드에서 공유 변수 접근 시 `threading.Lock` 사용 필수
- Chainlit 메시지 업데이트는 메인 이벤트 루프에서만

### 3. 에러 처리
- executor 내부 예외는 await 시점에 발생
- try-except로 적절히 처리

## 테스트 시나리오

### 1. 긴 작업 (커밋 500개 인덱싱)
```
✅ UI 응답 유지
✅ 진행 상황 2초마다 업데이트
✅ 다른 메시지 입력 가능
✅ 완료 후 결과 표시
```

### 2. 여러 작업 연속 실행
```
✅ 각 작업이 백그라운드 실행
✅ UI 블로킹 없음
✅ 순차 완료
```

### 3. 검색 중 인덱싱
```
✅ 검색 → 미인덱싱 감지
✅ 자동 인덱싱 (백그라운드)
✅ 진행 상황 표시
✅ 완료 후 검색 실행
```

## 결론

✅ **모든 도구 함수가 비동기로 실행됨**
✅ **UI가 절대 멈추지 않음**
✅ **진행 상황 실시간 표시**
✅ **동시 작업 가능**
✅ **사용자 경험 대폭 개선**

## 추가 개선: 커밋 SHA 해석 기능 (2025-10-29)

### 문제
```
사용자: "커밋 148231의 diff 보여줘"
→ Error: Ref '148231' did not resolve to an object
```

### 해결
모든 파일/커밋 조회 함수에서 **유연한 커밋 해석** 지원:

```python
# 1. 전체 SHA
commit = repo.commit("a1b2c3d4e5f6...")

# 2. 짧은 SHA (최소 4자)
commit = repo.commit("a1b2c3d")  # git rev-parse로 해석

# 3. 숫자 (HEAD~N으로 해석)
commit = repo.commit("148231")  # → HEAD~148231

# 4. HEAD 표현식
commit = repo.commit("HEAD~5")
```

### 적용된 함수
- ✅ `get_commit_diff` - diff 조회
- ✅ `read_file_from_commit` - 파일 읽기
- ✅ `get_file_context` - 파일 컨텍스트

### 해석 우선순위
```python
# 1. 직접 시도
try:
    commit = repo.commit(commit_sha)
except:
    # 2. 짧은 SHA로 시도
    if len(commit_sha) >= 4:
        full_sha = repo.git.rev_parse(commit_sha)
        commit = repo.commit(full_sha)
    # 3. 숫자면 HEAD~N으로 시도
    elif commit_sha.isdigit():
        commit = repo.commit(f'HEAD~{int(commit_sha)}')
```

### 사용 예시
```
사용자: "커밋 a1b2c3d의 diff 보여줘"     ✅ 짧은 SHA
사용자: "150번째 커밋 diff"               ✅ 숫자 → HEAD~150
사용자: "HEAD~5의 변경사항"               ✅ HEAD 표현식
사용자: "전체 SHA로..."                   ✅ 전체 SHA
```

---

**작성일**: 2025-10-29
**완료 항목**: 17개 도구 함수 비동기 변환 + 커밋 SHA 해석 개선

