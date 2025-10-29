# Git History Generator - 업데이트 내역

**날짜**: 2025-10-28  
**버전**: 1.1.0

---

## 🎯 주요 변경사항

### 1. LLM 및 임베딩 모델 변경

#### LLM 모델
- **변경 전**: `gpt-4.1-mini`
- **변경 후**: `wypark-gpt-4.1-mini`
- **위치**: `.env` 파일의 `AZURE_OPENAI_MODEL`

#### 임베딩 모델  
- **변경 전**: `text-embedding-3-small`
- **변경 후**: `wypark-text-embedding-3-small`
- **위치**: `.env` 파일의 `AZURE_OPENAI_EMBEDDING_MODEL`
- **벡터 차원**: 1536

### 2. 문서 메타데이터 강화

#### 추가된 메타데이터

##### 📋 Change Context (변경 컨텍스트)
최근 커밋 간 변경사항에 대한 문맥을 제공합니다.

**포함 정보**:
- `file_categories`: 파일 카테고리별 분류 (예: src, test, docs)
- `modified_files`: 수정된 파일 목록
- `added_files`: 새로 추가된 파일 목록
- `deleted_files`: 삭제된 파일 목록
- `impact_scope`: 변경의 영향 범위 (high/medium/low)

**구현 위치**: `src/document_generator.py` - `get_change_context()` 메서드

```python
def get_change_context(self, commit) -> Dict[str, Any]:
    """커밋의 변경 컨텍스트를 분석합니다."""
    # ...
```

##### 🔍 Function Analysis (함수 분석)
최근 커밋 간 수정된 함수/기능에 대한 리포지토리 내 소스 분석 문맥을 제공합니다.

**포함 정보**:
- `modified_functions`: 수정된 함수 목록 (함수명, 파일경로)
- `added_functions`: 추가된 함수 목록
- `removed_functions`: 제거된 함수 목록
- `modified_classes`: 수정된 클래스 목록
- `code_complexity_hint`: 코드 복잡도 힌트 (low/medium/high)
  - low: 변경 라인 수 < 20
  - medium: 20 ≤ 변경 라인 수 ≤ 100
  - high: 변경 라인 수 > 100

**구현 위치**: `src/document_generator.py` - `analyze_functions_in_commit()` 메서드

```python
def analyze_functions_in_commit(self, commit) -> Dict[str, Any]:
    """커밋에서 수정된 함수들을 분석합니다."""
    # Python 파일의 함수/클래스 변경 추적
    # ...
```

##### 🔗 Relation to Previous (이전 커밋과의 관계)
연속된 커밋 간의 관계를 파악합니다.

**포함 정보**:
- `common_files`: 이전 커밋과 공통으로 수정된 파일 목록
- `related_files`: 관련된 파일 목록
- `relationship_type`: 커밋 관계 유형
  - `sequential`: 일반적인 순차 커밋
  - `bugfix`: 버그 수정 (메시지에 "fix", "bug" 포함)
  - `feature`: 기능 추가 (메시지에 "feat", "add" 포함)
  - `refactor`: 리팩토링 (메시지에 "refactor" 포함)

**구현 위치**: `src/document_generator.py` - `get_commit_relation()` 메서드

```python
def get_commit_relation(self, commit, previous_commit) -> Dict[str, Any]:
    """현재 커밋과 이전 커밋 간의 관계를 분석합니다."""
    # ...
```

### 3. 디코딩 오류 처리 개선

#### 문제점
- 일부 파일에서 UTF-8 디코딩 실패 시 프로세스가 중단되거나 원인 파악이 어려움
- Exception 발생 시 로그에 상세 정보 부족

#### 개선 사항

##### 1) UTF-8 → latin-1 자동 폴백 (123라인)
```python
# 변경 전
diff_text = item.diff.decode('utf-8', errors='ignore')

# 변경 후
try:
    diff_text = item.diff.decode('utf-8')
except UnicodeDecodeError as ude:
    logger.debug(f"UTF-8 decode failed for {file_path}, trying latin-1: {ude}")
    diff_text = item.diff.decode('latin-1', errors='ignore')
```

##### 2) 상세 예외 로깅 추가 (129라인, 358라인)
```python
# 변경 전
except Exception:
    pass

# 변경 후  
except Exception as e:
    logger.warning(f"Failed to decode diff for {file_path}: {type(e).__name__} - {str(e)}")
    pass
```

##### 3) 정규식 경고 수정
```python
# 변경 전
removed_funcs = re.findall(r'^\-\s*def\s+(\w+)\s*\(', diff_text, re.MULTILINE)

# 변경 후
removed_funcs = re.findall(r'^-\s*def\s+(\w+)\s*\(', diff_text, re.MULTILINE)
```

**적용 위치**:
- `src/document_generator.py` - `get_commits()` 메서드 (123-138라인)
- `src/document_generator.py` - `analyze_functions_in_commit()` 메서드 (312-358라인)

### 4. 임베딩 모델 로깅 추가

실제 사용 중인 임베딩 모델을 확인하기 위한 로깅 추가:

```python
# src/embedding.py
EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# 임베딩 모델 로드 확인
logger.info(f"Using embedding model: {EMBEDDING_MODEL}")
```

---

## 📊 Azure AI Search 인덱스 스키마 변경

### 추가된 필드

```python
# 변경 컨텍스트
SearchableField(name="change_context_summary", type=SearchFieldDataType.String),
SearchableField(name="impact_scope", type=SearchFieldDataType.String),

# 함수 분석
SearchableField(name="modified_functions", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
SearchableField(name="modified_classes", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
SearchableField(name="code_complexity", type=SearchFieldDataType.String),

# 커밋 관계
SearchableField(name="relationship_type", type=SearchFieldDataType.String),
```

---

## 🧪 테스트 결과

### 테스트 커버리지
- ✅ 모델 초기화 테스트
- ✅ 문서 생성 및 메타데이터 테스트
- ✅ 임베딩 모델 테스트 (1536차원 벡터)
- ✅ 인덱싱 테스트 (메타데이터 포함)
- ✅ 검색 테스트 (하이브리드 검색)

### 성능 지표
| 항목 | 결과 |
|------|------|
| 문서 생성 (커밋 1개) | ~1초 |
| 임베딩 (3개 텍스트) | ~1초 |
| 인덱싱 (1개 커밋) | ~2초 |
| 검색 (쿼리 1개) | ~1초 |
| 문서 크기 (메타데이터 포함) | ~35KB |

**상세 테스트 보고서**: [`docs/TEST_REPORT.md`](./TEST_REPORT.md)

---

## 📁 변경된 파일 목록

### 수정된 파일
1. **`.env`** - 모델 배포 이름 업데이트
2. **`src/document_generator.py`** - 메타데이터 추가 및 디코딩 개선
3. **`src/embedding.py`** - 로깅 추가
4. **`src/indexer.py`** - 새 메타데이터 필드 인덱싱 지원

### 추가된 파일
1. **`test_functionality.py`** - 실제 기능 테스트 스크립트
2. **`docs/TEST_REPORT.md`** - 테스트 보고서
3. **`docs/UPDATE_SUMMARY.md`** - 이 문서

---

## 🔧 환경 설정 가이드

### 필수 환경변수 (.env)
```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_MODEL=wypark-gpt-4.1-mini
AZURE_OPENAI_EMBEDDING_MODEL=wypark-text-embedding-3-small

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your_search_key
AZURE_SEARCH_INDEX_NAME=git-commits

# 임베딩 설정
EMBEDDING_BATCH_SIZE=20
```

---

## 🚀 사용 방법

### 1. 테스트 실행
```bash
python test_functionality.py
```

### 2. Streamlit 앱 실행
```bash
streamlit run src/app.py
```

### 3. 커밋 인덱싱
```python
from src.indexer import CommitIndexer
from src.agent import initialize_models

llm_client, search_client, index_client = initialize_models()

indexer = CommitIndexer(
    search_client=search_client,
    index_client=index_client,
    openai_client=llm_client,
    index_name="git-commits"
)

# 인덱스 생성
indexer.create_index_if_not_exists(vector_dimensions=1536)

# 리포지토리 인덱싱
count = indexer.index_repository(".", limit=100)
print(f"Indexed {count} commits")
```

### 4. 커밋 검색
```python
from src.tools import search_commits

results = search_commits(
    query="bug fix",
    search_client=search_client,
    openai_client=llm_client,
    top=10
)

for result in results:
    print(f"{result['message']} - {result['author']}")
```

---

## 📝 다음 단계 (향후 개선 사항)

### 1. 성능 최적화
- [ ] 대량 커밋 처리 시 배치 처리 최적화
- [ ] 병렬 처리로 인덱싱 속도 향상
- [ ] 캐싱 메커니즘 추가

### 2. 기능 확장
- [ ] 다른 프로그래밍 언어 지원 (현재 Python만 함수 분석)
- [ ] 커밋 간 의존성 그래프 생성
- [ ] 자동화된 릴리즈 노트 생성

### 3. UI 개선
- [ ] Streamlit 앱에서 메타데이터 시각화
- [ ] 커밋 히스토리 타임라인 뷰
- [ ] 기여자 분석 대시보드

### 4. 분석 기능 강화
- [ ] 버그 패턴 분석
- [ ] 코드 품질 트렌드 분석
- [ ] 핫스팟 파일 식별

---

## 📞 문의 및 지원

문제가 발생하거나 개선 사항이 있으면 이슈를 등록해주세요.

**프로젝트 상태**: ✅ 안정 버전  
**최종 업데이트**: 2025-10-28

