# Azure AI Search Index 활용 가이드 - 빠른 시작

## 🎯 개요

이 프로젝트는 Azure AI Search를 활용하여 Git 커밋 히스토리를 인덱싱하고 검색할 수 있는 시스템입니다.

### 주요 기능
- ✅ Git 저장소 커밋 데이터 인덱싱 (로컬/GitHub)
- ✅ 자연어 기반 하이브리드 검색 (텍스트 + 벡터)
- ✅ 다중 저장소 관리
- ✅ 증분 인덱싱 (중복 제외)
- ✅ 인덱스 통계 및 관리

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성 및 설정
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_MODEL=gpt-4o-mini

AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
AZURE_SEARCH_API_KEY=your-search-api-key
AZURE_SEARCH_INDEX_NAME=git-commits
```

### 2. 채팅 앱 실행

```bash
chainlit run src/chat_app.py
```

### 3. 기본 사용법

#### 저장소 인덱싱
```
저장소 인덱싱해줘: https://github.com/username/repo
```

#### 커밋 검색
```
"로그인 기능" 관련 커밋 찾아줘
```

#### 인덱스 통계
```
인덱스 통계 보여줘
```

---

## 📖 주요 활용 방법

### 1️⃣ 현재 저장소 설정
```
현재 저장소 설정: https://github.com/myrepo/project
```
이후 모든 명령에서 저장소 경로를 생략할 수 있습니다.

### 2️⃣ 제한된 개수 인덱싱
```
최근 100개 커밋만 인덱싱해줘
```

### 3️⃣ 날짜 범위 인덱싱
```
2024년 커밋만 인덱싱해줘
since: 2024-01-01, until: 2024-12-31
```

### 4️⃣ 특정 저장소에서만 검색
```
현재 저장소 설정 후 "버그 수정" 관련 커밋 찾기
```

### 5️⃣ 인덱싱된 저장소 확인
```
인덱싱된 저장소 목록 보여줘
```

---

## 🔧 고급 기능

### 프로그래밍 방식 사용

```python
from src.indexer import CommitIndexer
from src.index_manager import IndexManager
from src.tools import search_commits

# 클라이언트 초기화
openai_client, search_client, index_client = initialize_clients()

# 인덱싱
indexer = CommitIndexer(search_client, index_client, openai_client, "git-commits")
indexer.create_index_if_not_exists()
indexed_count = indexer.index_repository(
    repo_path="https://github.com/user/repo",
    limit=100,
    skip_existing=True
)

# 검색
results = search_commits(
    query="authentication",
    search_client=search_client,
    openai_client=openai_client,
    top=10
)

# 인덱스 관리
manager = IndexManager(search_client, index_client, "git-commits")
stats = manager.get_index_statistics()
repos = manager.list_indexed_repositories()
health = manager.check_index_health()
```

### 예제 스크립트 실행

```bash
python examples/index_usage_examples.py
```

9가지 실용 예제 제공:
1. 기본 인덱싱
2. 인덱스 통계 확인
3. 인덱싱된 저장소 목록
4. 커밋 검색
5. 특정 저장소 정보 조회
6. 인덱스 상태 확인
7. 증분 인덱싱
8. 다중 저장소 인덱싱 및 통합 검색
9. 날짜 범위 인덱싱

---

## 📊 제공되는 도구 (채팅 앱)

### 인덱싱 관련
- `index_repository`: 저장소 인덱싱
- `set_current_repository`: 현재 저장소 설정

### 검색 관련
- `search_commits`: 자연어 커밋 검색
- `get_commit_summary`: 커밋 요약
- `analyze_contributors`: 기여자 분석
- `find_bug_commits`: 버그 수정 커밋 찾기

### 관리 관련
- `get_index_statistics`: 인덱스 통계
- `list_indexed_repositories`: 저장소 목록
- `get_repository_info`: 저장소 상세 정보
- `delete_repository_commits`: 저장소 삭제
- `check_index_health`: 인덱스 상태 확인

### 파일 읽기
- `read_file_from_commit`: 특정 커밋의 파일 내용
- `get_file_context`: 파일 변경 컨텍스트
- `get_commit_diff`: 커밋 diff
- `get_readme`: README 내용

---

## 🎨 실전 시나리오

### 시나리오 1: 신규 프로젝트 분석
```
1. 저장소 인덱싱: https://github.com/microsoft/playwright (최근 1000개)
2. README 확인
3. "test automation" 관련 커밋 검색
4. 기여자 분석
```

### 시나리오 2: 특정 기능 개발 히스토리 추적
```
1. 현재 저장소 설정
2. 저장소 인덱싱 (전체)
3. "authentication" 관련 커밋 검색 (top 20)
4. 각 커밋의 diff 확인
```

### 시나리오 3: 다중 저장소 비교 분석
```
1. 여러 저장소 인덱싱 (React, Vue, Angular)
2. "hooks implementation" 통합 검색
3. 각 저장소별로 어떻게 구현했는지 비교
```

---

## 🔍 검색 품질 향상 팁

### 효과적인 쿼리 작성
- ✅ 구체적으로: "로그인 버그 수정"
- ❌ 모호하게: "fix"

- ✅ 맥락 포함: "결제 모듈 리팩토링"
- ❌ 단어만: "code"

### 하이브리드 검색 활용
시스템은 자동으로 **텍스트 검색 + 벡터 검색**을 결합하여 최적의 결과를 제공합니다.

---

## ⚙️ 성능 최적화

### 환경 변수로 제한 설정
```env
MAX_COMMIT_LIMIT=200        # 최대 커밋 제한
MAX_SEARCH_TOP=20           # 최대 검색 결과
MAX_CONTRIBUTOR_LIMIT=500   # 기여자 분석 제한
```

### 권장 사항
- 처음에는 제한된 개수로 시작 (`limit=100`)
- 증분 인덱싱 활용 (`skip_existing=True`)
- 필요한 날짜 범위만 인덱싱
- 특정 저장소로 검색 필터링

---

## 🛠️ 문제 해결

### 인덱싱 실패
- `.env` 파일의 Azure 자격 증명 확인
- 저장소 경로가 올바른지 확인
- GitHub 토큰 설정 (private repo)

### 검색 결과 없음
- Azure Portal에서 인덱스 확인
- 재인덱싱 시도 (`skip_existing=False`)
- 쿼리를 더 구체적으로 또는 일반적으로 수정

### 성능 저하
- `top` 값 줄이기 (10 이하)
- 특정 저장소로 필터링
- Azure Search tier 업그레이드 고려

---

## 📚 참고 문서

- [상세 가이드](./AZURE_SEARCH_INDEX_GUIDE.md)
- [Azure AI Search 공식 문서](https://learn.microsoft.com/azure/search/)
- [Vector Search 가이드](https://learn.microsoft.com/azure/search/vector-search-overview)

---

## 📝 요약

### 핵심 워크플로우
```
저장소 경로 → 인덱싱 → Azure AI Search → 자연어 검색 → 하이브리드 결과 → 컨텍스트 분석
```

### 기본 명령어
1. **인덱싱**: "저장소 인덱싱해줘"
2. **검색**: "xxx 관련 커밋 찾아줘"
3. **설정**: "현재 저장소 설정"
4. **통계**: "인덱스 통계 보여줘"

---

**업데이트**: 2025-10-28

