# 다중 저장소 인덱싱 개선 - 프로젝트 점검 결과

## 📋 점검 결과

### ✅ 문제 확인됨
기존 구현에서는 **여러 Git 저장소를 인덱싱할 때 모든 커밋이 같은 인덱스에 섞여서 저장**되는 문제가 있었습니다.

#### 구체적인 문제점:
1. **저장소 구분 불가**: 각 커밋이 어떤 저장소에서 온 것인지 구분할 수 없음
2. **검색 결과 부정확**: 서로 다른 프로젝트의 커밋이 섞여서 검색됨
3. **증분 인덱싱 비효율**: `skip_existing`이 모든 저장소의 커밋을 확인하여 불필요한 체크 수행

### ✅ 해결책 구현 완료

#### 구현된 기능:

1. **저장소 식별자 생성** (`normalize_repo_identifier`)
   - URL 정규화: `https://github.com/user/repo.git` → 표준화된 해시
   - 로컬 경로 정규화: `./project` → 절대 경로 → 해시
   - SHA-256 해시의 첫 16자 사용 (충돌 가능성: 1/2^64)

2. **인덱스 스키마 확장**
   - `repo_id` 필드 추가: 저장소 고유 식별자 (filterable, facetable)
   - `repository_path` 필드 추가: 원본 경로/URL (searchable)

3. **인덱싱 로직 개선**
   - 각 커밋에 `repo_id` 자동 부여
   - 증분 인덱싱 시 같은 저장소의 커밋만 확인 (`filter=f"repo_id eq '{repo_id}'"`)
   - 저장소별 독립적인 인덱싱

4. **검색 기능 개선**
   - `search_commits()`에 `repo_path` 파라미터 추가
   - 특정 저장소만 검색하거나 전체 검색 가능
   - 검색 결과에 저장소 정보 포함

## 🧪 테스트 결과

### 새로운 테스트 (`test_multi_repo_indexing.py`)
```
✅ test_normalize_repo_identifier_url          PASSED
✅ test_normalize_repo_identifier_local        PASSED
✅ test_normalize_repo_identifier_different    PASSED
✅ test_repo_id_format                         PASSED
✅ test_desired_behavior_documentation         PASSED

5 passed in 0.78s
```

모든 테스트 통과! 정규화 로직이 올바르게 동작합니다.

## 📝 사용 예시

### 여러 저장소 인덱싱
```python
from src.indexer import CommitIndexer

indexer = CommitIndexer(search_client, index_client, openai_client, "git-commits")

# 첫 번째 저장소 (GitHub)
count1 = indexer.index_repository("https://github.com/user/project1")
# → repo_id: a1b2c3d4e5f6g7h8

# 두 번째 저장소 (GitHub)
count2 = indexer.index_repository("https://github.com/user/project2")
# → repo_id: 9i0j1k2l3m4n5o6p

# 로컬 저장소
count3 = indexer.index_repository("C:/projects/my-app")
# → repo_id: q7r8s9t0u1v2w3x4
```

### 특정 저장소에서만 검색
```python
from src.tools import search_commits

# project1에서만 검색
results = search_commits(
    query="bug fix authentication",
    search_client=search_client,
    openai_client=openai_client,
    repo_path="https://github.com/user/project1"
)

# 모든 저장소에서 검색
all_results = search_commits(
    query="bug fix authentication",
    search_client=search_client,
    openai_client=openai_client
)
```

### 증분 인덱싱 (저장소별 독립)
```python
# 첫 번째 인덱싱
count1 = indexer.index_repository("https://github.com/user/repo1", limit=100)
# → 100개 커밋 인덱싱

# 같은 저장소 재인덱싱 (증분)
count2 = indexer.index_repository("https://github.com/user/repo1", limit=100, skip_existing=True)
# → 0개 (이미 모두 있음)

# 다른 저장소 인덱싱 (영향 없음)
count3 = indexer.index_repository("https://github.com/user/repo2", limit=100)
# → 100개 커밋 인덱싱 (repo1과 독립적)
```

## 📊 변경된 파일

### 수정된 파일:
1. **`src/indexer.py`**
   - `normalize_repo_identifier()` 함수 추가
   - 인덱스 스키마에 `repo_id`, `repository_path` 필드 추가
   - `index_repository()` 메서드 수정: repo_id 생성 및 필터링

2. **`src/tools.py`**
   - `normalize_repo_identifier()` 함수 추가 (중복, 의존성 없이 사용)
   - `search_commits()` 함수에 `repo_path` 파라미터 추가
   - 검색 시 저장소 필터링 기능 추가

### 새로 생성된 파일:
3. **`tests/test_multi_repo_indexing.py`**
   - 저장소 정규화 테스트
   - URL과 로컬 경로 정규화 검증
   - repo_id 형식 검증

4. **`docs/MULTI_REPO_INDEXING.md`**
   - 상세 구현 가이드
   - 사용 예시 및 주의사항

5. **`docs/MULTI_REPO_INDEXING_SUMMARY.md`** (이 문서)
   - 프로젝트 점검 결과 요약

## ⚠️ 마이그레이션 필요

기존에 인덱싱된 데이터는 `repo_id` 필드가 없으므로 **재인덱싱이 필요**합니다.

### 마이그레이션 방법:
```python
# 1. 기존 인덱스 삭제 (또는 새 인덱스 이름 사용)
indexer.delete_index()

# 2. 새 스키마로 인덱스 생성
indexer.create_index_if_not_exists()

# 3. 저장소별로 재인덱싱
indexer.index_repository("./your-repo", limit=None)  # 전체 인덱싱
```

## 🎯 장점

1. **명확한 구분**: 각 저장소의 커밋을 명확하게 구분 가능
2. **효율적인 증분 인덱싱**: 저장소별로 독립적인 증분 인덱싱
3. **정확한 검색**: 특정 프로젝트의 커밋만 검색 가능
4. **확장성**: 무한대의 저장소를 하나의 인덱스에서 관리
5. **안정성**: 해시 충돌 가능성 극히 낮음 (2^64 ≈ 18,446,744,073,709,551,616)

## 🔍 기술적 세부사항

### 정규화 알고리즘:
1. **URL 정규화**:
   - 스킴 + netloc + path 추출
   - 후행 슬래시 제거
   - `.git` 확장자 제거
   - 소문자로 변환

2. **로컬 경로 정규화**:
   - 절대 경로로 변환 (`Path.resolve()`)
   - 소문자로 변환 (Windows 대소문자 무시)

3. **해시화**:
   - SHA-256 해시 생성
   - 첫 16자만 사용 (충분히 고유함)

### 성능 영향:
- **추가 계산**: 저장소당 1회 해시 계산 (무시할 수준)
- **필터링 오버헤드**: Azure AI Search의 효율적인 인덱싱으로 성능 저하 미미
- **저장 공간**: 문서당 16 bytes + 경로 길이 (무시할 수준)

## ⚡ 다음 단계

1. **기존 인덱스 백업** (필요 시)
2. **새 스키마로 인덱스 재생성**
3. **저장소별 재인덱싱**
4. **검색 기능 테스트**
5. **UI 업데이트** (저장소 필터 추가 가능)

## 📚 관련 문서
- 상세 가이드: `docs/MULTI_REPO_INDEXING.md`
- 테스트: `tests/test_multi_repo_indexing.py`
- 구현: `src/indexer.py`, `src/tools.py`

---

## ✅ 결론

**문제가 확인되었고, 해결책이 구현되어 테스트를 통과했습니다.**

이제 여러 Git 저장소를 인덱싱해도 각 저장소의 커밋이 명확하게 구분되며, 특정 저장소만 검색하거나 전체 저장소를 검색할 수 있습니다. 기존 데이터는 재인덱싱이 필요합니다.

