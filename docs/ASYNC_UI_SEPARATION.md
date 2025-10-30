# 비동기 UI 분리 개요

- 모든 블로킹 작업(Git, 네트워크, CPU)은 `run_in_executor`로 오프로딩
- Chainlit Step으로 진행 상태 노출, Socket 페이로드는 요약/절단
- 긴 작업은 배치/분할 처리(대용량 인덱싱)
- shallow clone → 필요 시 deepen(fetch depth 증가)로 skip_offset 대응

핵심 이점
- UI 프리즈 방지, 장시간 작업에도 세션 안정
- 오류/재시도 포인트가 명확(로그/Step)
