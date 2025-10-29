# 다중 저장소 인덱싱 개선

## 문제점
기존 구현에서는 여러 Git 저장소를 인덱싱할 때 모든 커밋이 같은 Azure AI Search 인덱스에 저장되었습니다. 이로 인해:
1. **저장소 구분 불가**: 검색 시 어떤 저장소의 커밋인지 구분할 수 없었습니다
2. **데이터 혼합**: 서로 다른 프로젝트의 커밋이 섞여서 검색 결과가 부정확해질 수 있었습니다
3. **증분 인덱싱 오류**: `skip_existing` 기능이 모든 저장소의 커밋을 확인하여 비효율적이었습니다

## 해결책
저장소 URL 또는 로컬 경로를 정규화하고 해시화하여 각 저장소를 고유하게 식별합니다.

### 구현 내역

#### 1. 저장소 식별자 생성 (`normalize_repo_identifier`)
```python
def normalize_repo_identifier(repo_path: str) -> str:
    """
    저장소 경로 또는 URL을 정규화된 식별자로 변환합니다.
    
    Args:
        repo_path: Git 저장소 경로 또는 URL
        
    Returns:
        str: 정규화된 저장소 식별자 (해시값)
    """
```

**정규화 로직**:
- **URL**: `https://github.com/user/repo.git` → `https://github.com/user/repo`
  - 스킴, netloc, path를 표준화
  - `.git` 확장자 제거
  - 소문자로 변환
  
- **로컬 경로**: `./my-project` → `c:\users\user\projects\my-project`
  - 절대 경로로 변환
  - 소문자로 변환

- **해시화**: SHA-256 해시의 첫 16자를 사용 (충돌 가능성 극히 낮음)

#### 2. 인덱스 스키마 확장
새로운 필드 추가:
- `repo_id` (SimpleField, filterable): 저장소 식별자 (16자 해시)
- `repository_path` (SearchableField): 원본 저장소 경로/URL

#### 3. 인덱싱 로직 개선
`CommitIndexer.index_repository()`:
- 저장소별로 고유한 `repo_id` 생성
- 증분 인덱싱 시 같은 저장소의 커밋만 확인 (`filter=f"repo_id eq '{repo_id}'"`)
- 모든 문서에 `repo_id`와 `repository_path` 추가

#### 4. 검색 기능 개선
`search_commits()`:
- 선택적 `repo_path` 파라미터 추가
- 특정 저장소의 커밋만 검색 가능
- 검색 결과에 저장소 정보 포함

### 사용 예시

#### 여러 저장소 인덱싱
```python
indexer = CommitIndexer(search_client, index_client, openai_client, "git-commits")

# 첫 번째 저장소
indexer.index_repository("https://github.com/user/repo1")

# 두 번째 저장소
indexer.index_repository("https://github.com/user/repo2")

# 로컬 저장소
indexer.index_repository("./my-local-project")
```

각 저장소의 커밋은 고유한 `repo_id`로 구분되어 저장됩니다.

#### 특정 저장소에서만 검색
```python
# repo1에서만 검색
results = search_commits(
    "bug fix",
    search_client,
    openai_client,
    repo_path="https://github.com/user/repo1"
)

# 모든 저장소에서 검색
results = search_commits(
    "bug fix",
    search_client,
    openai_client
)
```

#### 증분 인덱싱
```python
# 첫 번째 인덱싱: 100개 커밋 추가
count1 = indexer.index_repository("https://github.com/user/repo1", limit=100)
# → 100개 인덱싱됨

# 두 번째 인덱싱: 같은 저장소, 기존 커밋 건너뛰기
count2 = indexer.index_repository("https://github.com/user/repo1", limit=100, skip_existing=True)
# → 0개 인덱싱됨 (이미 모두 있음)

# 다른 저장소: 영향받지 않음
count3 = indexer.index_repository("https://github.com/user/repo2", limit=100)
# → 100개 인덱싱됨 (repo1과 독립적)
```

### 기존 인덱스 마이그레이션

기존에 `repo_id` 필드 없이 인덱싱된 데이터가 있다면:
1. 새 인덱스 생성 (또는 기존 인덱스 삭제)
2. 저장소별로 재인덱싱

```python
# 기존 인덱스 삭제
indexer.delete_index()

# 새 스키마로 인덱스 생성
indexer.create_index_if_not_exists()

# 저장소별로 재인덱싱
indexer.index_repository("./my-project")
```

### 장점
1. **명확한 구분**: 각 저장소의 커밋을 명확하게 구분
2. **효율적인 증분 인덱싱**: 저장소별로 독립적인 증분 인덱싱
3. **정확한 검색**: 특정 프로젝트의 커밋만 검색 가능
4. **확장성**: 무한대의 저장소를 하나의 인덱스에서 관리 가능
5. **안정성**: 해시 충돌 가능성 극히 낮음 (2^64 = 약 18경 개)

### 주의사항
1. **인덱스 스키마 변경**: 기존 인덱스와 호환되지 않음 (재인덱싱 필요)
2. **저장소 경로 일관성**: 같은 저장소를 다른 경로로 지정하면 다른 `repo_id` 생성됨
   - 예: `./project` vs `C:\Users\User\project`
   - 해결: 항상 절대 경로 또는 표준 URL 사용
3. **성능**: 필터링 추가로 약간의 성능 오버헤드 (무시할 수준)

### 테스트
`tests/test_multi_repo_indexing.py`에 다중 저장소 테스트 추가됨.

### 관련 파일
- `src/indexer.py`: 인덱싱 로직
- `src/tools.py`: 검색 기능
- `tests/test_multi_repo_indexing.py`: 테스트

