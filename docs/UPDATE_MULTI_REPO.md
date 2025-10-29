# 다중 저장소 인덱싱 개선 - 업데이트 노트

**날짜**: 2025년 10월 28일

## 🎯 업데이트 요약

여러 Git 저장소를 인덱싱할 때 각 저장소의 커밋을 명확하게 구분하고 독립적으로 관리할 수 있는 기능이 추가되었습니다.

## 📦 새로운 기능

### 1. 저장소 식별자 시스템
- 각 저장소에 고유한 `repo_id` 할당 (16자 해시)
- URL과 로컬 경로 자동 정규화
- 동일한 저장소를 다양한 방식으로 참조해도 같은 ID 생성

### 2. 저장소별 필터링
- 특정 저장소의 커밋만 검색 가능
- 증분 인덱싱 시 같은 저장소의 커밋만 확인
- 검색 결과에 저장소 정보 포함

### 3. 독립적인 인덱싱
- 여러 저장소를 하나의 인덱스에서 관리
- 저장소별로 독립적인 증분 인덱싱
- 서로 다른 프로젝트 커밋이 섞이지 않음

## 🔧 변경 사항

### 인덱스 스키마
새로운 필드 추가:
- `repo_id` (SimpleField): 저장소 식별자
- `repository_path` (SearchableField): 원본 저장소 경로/URL

### API 변경
- `search_commits()`: `repo_path` 파라미터 추가 (선택적)
- `index_repository()`: 내부적으로 `repo_id` 자동 생성 및 할당

## 📖 사용 예시

### 여러 저장소 인덱싱
```python
from src.indexer import CommitIndexer

# 여러 저장소 인덱싱
indexer.index_repository("https://github.com/user/project1")
indexer.index_repository("https://github.com/user/project2")
indexer.index_repository("./local-project")
```

### 특정 저장소 검색
```python
from src.tools import search_commits

# project1에서만 검색
results = search_commits(
    "bug fix",
    search_client,
    openai_client,
    repo_path="https://github.com/user/project1"
)
```

## ⚠️ 호환성

### 기존 인덱스
기존에 인덱싱된 데이터는 `repo_id` 필드가 없으므로 **재인덱싱이 필요**합니다.

### 마이그레이션
```python
# 1. 기존 인덱스 삭제
indexer.delete_index()

# 2. 새 스키마로 생성
indexer.create_index_if_not_exists()

# 3. 재인덱싱
indexer.index_repository("./your-repo")
```

## 📚 문서
- 상세 가이드: [`docs/MULTI_REPO_INDEXING.md`](./MULTI_REPO_INDEXING.md)
- 점검 결과: [`docs/MULTI_REPO_INDEXING_SUMMARY.md`](./MULTI_REPO_INDEXING_SUMMARY.md)
- 테스트: [`tests/test_multi_repo_indexing.py`](../tests/test_multi_repo_indexing.py)

## ✅ 테스트 결과
```
✅ 5개 테스트 모두 통과
✅ URL 정규화 검증 완료
✅ 로컬 경로 정규화 검증 완료
✅ repo_id 형식 검증 완료
```

## 🎉 장점
- ✅ 명확한 저장소 구분
- ✅ 효율적인 증분 인덱싱
- ✅ 정확한 검색 결과
- ✅ 무한대의 저장소 관리 가능
- ✅ 해시 충돌 가능성 극히 낮음

---

**구현 완료 및 테스트 통과** ✨

