# Azure AI Search 인덱스 가이드(요약)

## 스키마(요약)
- id (key), message, author, date, repository_path, repo_id
- files_summary, parents, stats(선택)
- 벡터 필드: message_vector (1536)

## 생성/업데이트
- 앱에서 자동 생성(`create_index_if_not_exists`)
- upsert 기반 증분 인덱싱

## 조회 팁
- 저장소별: `filter="repo_id eq '<id>'"`
- 날짜 범위: `date ge 2025-01-01T00:00:00Z and date le 2025-12-31T23:59:59Z`
- 정렬: `order_by=["date desc"]`

## 하이브리드 검색
- text + vector 결합, rerank는 LLM 요약으로 대체
- 결과가 많을 때는 top을 작게, 페이지네이션 권장

## 운영 팁
- 대용량 upsert는 배치로(네트워크 안정성↑)
- 도큐먼트 크기 줄이기: files_summary 요약/절단
- 장애 시: 인덱스 헬스 체크 → 필요 시 재생성
