# Azure AI Search Index 활용 가이드

## 목차
1. [현재 구현 상태](#현재-구현-상태)
2. [기본 사용법](#기본-사용법)
3. [고급 활용 방법](#고급-활용-방법)
4. [실전 시나리오](#실전-시나리오)
5. [최적화 팁](#최적화-팁)
6. [문제 해결](#문제-해결)

---

## 현재 구현 상태

### 📦 주요 컴포넌트

#### 1. **CommitIndexer** (`src/indexer.py`)
- Git 커밋 데이터를 Azure AI Search에 인덱싱
- 벡터 검색 지원 (임베딩 기반)
- 증분 인덱싱 (이미 인덱싱된 커밋 건너뛰기)
- 다중 저장소 지원

#### 2. **search_commits** (`src/tools.py`)
- 자연어 쿼리로 커밋 검색
- 하이브리드 검색 (텍스트 + 벡터)
- 특정 저장소 필터링

#### 3. **채팅 앱 통합** (`src/chat_app.py`)
- `index_repository`: 저장소 인덱싱
- `search_commits`: 커밋 검색
- `set_current_repository`: 현재 저장소 설정

---

## 기본 사용법

### 1. 저장소 인덱싱

#### 전체 저장소 인덱싱
```
저장소를 인덱싱해줘: https://github.com/username/repo
```

**제한 사항**: 기본 500개 커밋으로 제한 (환경 변수로 조정 가능)

#### 특정 개수만 인덱싱
```
최근 100개 커밋만 인덱싱해줘: https://github.com/username/repo
```

#### 날짜 범위 인덱싱
```
2024년 커밋만 인덱싱해줘: https://github.com/username/repo
since: 2024-01-01, until: 2024-12-31
```

#### 로컬 저장소 인덱싱
```
로컬 저장소 인덱싱: C:/projects/my-repo
```

### 2. 커밋 검색

#### 자연어 검색
```
"로그인 기능" 관련 커밋 찾아줘
"버그 수정" 커밋 검색
"performance improvement" 관련 변경사항
```

#### 특정 저장소에서만 검색
```
현재 저장소 설정: https://github.com/username/repo
그 다음: "로그인 기능" 관련 커밋 찾아줘
```

---

## 고급 활용 방법

### 1. 증분 인덱싱 전략

#### 시나리오: 정기적으로 업데이트되는 저장소
```python
# 첫 번째 인덱싱 (전체)
index_repository(
    repo_path="https://github.com/user/repo",
    limit=1000,
    skip_existing=False  # 전체 인덱싱
)

# 나중에 새로운 커밋만 추가
index_repository(
    repo_path="https://github.com/user/repo",
    limit=100,  # 최근 100개만 확인
    skip_existing=True  # 이미 있는 건 건너뛰기
)
```

#### 채팅 앱에서:
```
저장소 업데이트: https://github.com/user/repo
(최근 100개만 인덱싱, 중복 제외)
```

### 2. 다중 저장소 관리

#### 여러 저장소 인덱싱
```python
repos = [
    "https://github.com/microsoft/vscode",
    "https://github.com/facebook/react",
    "https://github.com/tensorflow/tensorflow"
]

for repo in repos:
    index_repository(repo_path=repo, limit=500)
```

#### 채팅 앱에서:
```
1. VSCode 저장소 인덱싱: https://github.com/microsoft/vscode
2. React 저장소 인덱싱: https://github.com/facebook/react
3. 통합 검색: "hooks implementation" 찾기
   (모든 인덱싱된 저장소에서 검색)
```

### 3. 컨텍스트 기반 검색

#### Index 스키마에 포함된 메타데이터:
- `change_context_summary`: 변경 컨텍스트 요약
- `impact_scope`: 영향 범위
- `modified_functions`: 수정된 함수 목록
- `modified_classes`: 수정된 클래스 목록
- `code_complexity`: 코드 복잡도
- `relationship_type`: 관계 타입

#### 활용 예시:
```
고복잡도 커밋 찾기: code_complexity='high'
특정 클래스 수정: modified_classes contains 'UserService'
리팩토링 커밋: relationship_type='refactor'
```

---

## 실전 시나리오

### 시나리오 1: 신규 프로젝트 분석

**목표**: 오픈소스 프로젝트를 분석하여 주요 변경사항 파악

```
1. 저장소 인덱싱: https://github.com/microsoft/playwright
   (최근 1000개 커밋)

2. README 확인: get_readme

3. 주요 기능 검색: "test automation" 관련 커밋

4. 버그 수정 분석: "bug fix" 커밋 찾기

5. 기여자 분석: analyze_contributors
```

### 시나리오 2: 특정 기능 개발 히스토리 추적

**목표**: "인증" 기능이 어떻게 발전했는지 추적

```
1. 현재 저장소 설정: https://github.com/mycompany/app

2. 저장소 인덱싱 (전체)

3. 검색: "authentication" 관련 커밋 (top 20)

4. 각 커밋의 diff 확인:
   - get_commit_diff(commit_sha='abc123')

5. 파일 변경 컨텍스트 확인:
   - get_file_context(commit_sha='abc123', file_path='auth.py')
```

### 시나리오 3: 버그 패턴 분석

**목표**: 반복되는 버그 패턴 발견

```
1. 저장소 인덱싱 (최근 500개)

2. 버그 커밋 찾기: find_bug_commits

3. 검색: "memory leak" 관련 커밋

4. 기여자별 버그 수정 분석: analyze_contributors

5. 패턴 도출: LLM에게 분석 요청
```

### 시나리오 4: 코드 리뷰 준비

**목표**: PR 전 유사한 변경사항 확인

```
1. 현재 작업 중인 기능: "결제 시스템"

2. 검색: "payment" 관련 커밋

3. 유사 커밋 diff 확인

4. 놓친 부분 체크

5. 리뷰어에게 컨텍스트 제공
```

---

## 최적화 팁

### 1. 인덱싱 성능 최적화

#### ✅ 권장 사항
- **처음에는 제한된 개수로 시작**: `limit=500`
- **필요시 증분 인덱싱**: `skip_existing=True`
- **날짜 범위 활용**: 최근 1년만 인덱싱
- **배치 처리**: 대용량 저장소는 여러 번에 나눠 인덱싱

#### ❌ 피해야 할 것
- 한 번에 수천 개 커밋 인덱싱 (비용 폭탄)
- 같은 저장소 중복 인덱싱
- 불필요한 전체 인덱싱

### 2. 검색 품질 향상

#### 효과적인 쿼리 작성
```
❌ 나쁜 예: "fix"
✅ 좋은 예: "로그인 버그 수정"

❌ 나쁜 예: "code"
✅ 좋은 예: "결제 모듈 리팩토링"

❌ 나쁜 예: "change"
✅ 좋은 예: "API 엔드포인트 추가"
```

#### 하이브리드 검색 활용
- **텍스트 검색**: 정확한 키워드 매칭
- **벡터 검색**: 의미적 유사성
- 두 가지가 결합되어 최적의 결과 제공

### 3. 비용 최적화

#### 환경 변수 설정
```env
# .env 파일
MAX_COMMIT_LIMIT=200        # 최대 커밋 제한
MAX_SEARCH_TOP=20           # 최대 검색 결과
MAX_CONTRIBUTOR_LIMIT=500   # 기여자 분석 제한
MAX_TOOL_RESULT_TO_LLM=4000 # LLM에 전달할 최대 문자 수
```

#### 모니터링
- Azure Portal에서 인덱스 크기 확인
- 쿼리 수 모니터링
- 임베딩 API 호출 수 추적

---

## 문제 해결

### 1. 인덱싱 실패

#### 문제: "Failed to create index"
**원因**: Azure Search 자격 증명 오류

**해결**:
```bash
# .env 파일 확인
AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
AZURE_SEARCH_API_KEY=your-api-key
AZURE_SEARCH_INDEX_NAME=git-commits
```

#### 문제: "Repository not found"
**원因**: Git 저장소 경로 오류

**해결**:
- 로컬 경로: 절대 경로 사용
- GitHub URL: 정확한 URL 확인
- 인증 필요한 저장소: GitHub 토큰 설정

### 2. 검색 결과 없음

#### 문제: 검색해도 결과가 없음
**원因**: 인덱싱이 안 되어 있거나 쿼리 문제

**해결**:
```
1. 인덱스 확인: Azure Portal에서 문서 수 확인
2. 재인덱싱: skip_existing=False로 전체 재인덱싱
3. 쿼리 수정: 더 구체적이거나 더 일반적으로
```

### 3. 성능 저하

#### 문제: 검색이 너무 느림
**원因**: 인덱스 크기, 네트워크 등

**해결**:
- `top` 값 줄이기 (10 이하)
- 특정 저장소로 필터링
- Azure Search tier 업그레이드 고려

### 4. SocketIO Payload 에러

#### 문제: "Payload too large"
**원因**: 결과 데이터가 너무 큼

**해결**: 이미 구현됨
```python
MAX_TOOL_RESULT_DISPLAY = 300   # UI 표시 제한
MAX_TOOL_RESULT_TO_LLM = 4000   # LLM 전달 제한
```

---

## 추가 개선 아이디어

### 1. 인덱스 관리 도구 추가

```python
# 제안: 새로운 도구 함수
def manage_index(action: str, repo_path: Optional[str] = None):
    """
    인덱스 관리
    - list: 인덱싱된 저장소 목록
    - stats: 통계 정보
    - delete: 특정 저장소 삭제
    - clear: 전체 인덱스 초기화
    """
    pass
```

### 2. 자동 인덱싱 스케줄러

```python
# 제안: 정기적 업데이트
def schedule_indexing(repo_path: str, interval_hours: int):
    """정기적으로 저장소를 업데이트"""
    pass
```

### 3. 인덱스 품질 개선

```python
# 제안: 더 풍부한 메타데이터
- 파일 확장자별 통계
- 테스트 커버리지 변화
- 코드 리뷰 상태
- CI/CD 결과
```

### 4. 대시보드 추가

```python
# 제안: Streamlit 대시보드
- 인덱싱된 저장소 목록
- 검색 히트맵
- 기여자 통계
- 인덱스 상태 모니터링
```

---

## 참고 자료

- [Azure AI Search 문서](https://learn.microsoft.com/azure/search/)
- [Vector Search 가이드](https://learn.microsoft.com/azure/search/vector-search-overview)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)

---

## 요약

### 핵심 워크플로우

```mermaid
graph LR
    A[저장소 경로] --> B[인덱싱]
    B --> C[Azure AI Search]
    C --> D[자연어 검색]
    D --> E[하이브리드 결과]
    E --> F[컨텍스트 분석]
```

### 기본 명령어
1. **인덱싱**: "저장소 인덱싱해줘"
2. **검색**: "xxx 관련 커밋 찾아줘"
3. **설정**: "현재 저장소 설정"
4. **분석**: "기여자 분석해줘"

### 모범 사례
- ✅ 처음에는 제한된 개수로 시작
- ✅ 증분 인덱싱 활용
- ✅ 구체적인 쿼리 작성
- ✅ 특정 저장소 필터링
- ✅ 비용 모니터링

---

**업데이트**: 2025-10-28
**버전**: 1.0

