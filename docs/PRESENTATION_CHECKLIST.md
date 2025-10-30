# 발표 체크리스트

이 문서는 발표 직전 5분 점검표입니다. 빠르게 훑고 라이브 데모에 바로 들어갈 수 있도록 구성했습니다.

## 1) 핵심 자료
- [x] README 최신화 및 라이브 데모 링크: https://ktds-edu.ddns.dominico966.net/
- [x] 데모 스크립트: docs/DEMO_SCRIPT.md
- [x] Q&A 예상 질문: docs/QNA.md
- [ ] 스크린샷(선택): 초기 화면, 인덱싱 진행 화면, 검색 결과 화면 3장 이상
- [ ] 30초 데모 영상(선택): 장애 시 대체 재생용

## 2) 환경 변수(필수)
아래 값이 배포 환경에 정확히 세팅되어야 합니다.
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_VERSION (예: 2024-02-01)
- AZURE_OPENAI_MODEL (예: gpt-4o-mini 또는 배포명)
- AZURE_OPENAI_EMBEDDING_MODEL (예: text-embedding-3-small)
- AZURE_SEARCH_ENDPOINT
- AZURE_SEARCH_API_KEY
- AZURE_SEARCH_INDEX_NAME (예: git-commits)

체크: on_chat_start 로그에 "Clients initialized successfully"가 보여야 정상.

## 3) 프록시/인프라 체크(WebSocket)
- [x] /ws 경로가 101 Switching Protocols 업그레이드 되는지 확인
- [x] 프록시에서 헤더 전달: Upgrade: websocket, Connection: Upgrade
- [x] 타임아웃/버퍼 설정 충분히 확보
- [x] 서브패스 배포 시 root_path 일치 확인

브라우저 Network 탭에서 /ws 요청 상태코드와 에러(401/403/404) 여부 확인.

## 4) 데모 리허설
- [x] 초기화 → 스타터 노출 확인
- [x] set_current_repository 없이도 검색 시 인덱싱 허용 안내/진행 흐름 확인
- [x] "인덱스 통계 보여줘" 질의 응답 확인
- [x] "버그 커밋 찾아줘" 결과 1~2건 노출 확인
- [x] 에러 메시지/예외시 사용자 안내 문구 확인

## 5) 발표 흐름(권장)
1. 문제정의: 커밋 히스토리에서 통찰을 빠르게 얻기 어렵다
2. 해결책: AI + Azure Search + 대화형 UI로 자연어 분석/검색
3. 아키텍처: UI → Agent → Tools → Azure
4. 데모: 인덱싱 → 검색/요약 → 기여자/버그 분석 → Diff 미리보기
5. 기술 포인트: 증분 인덱싱, 하이브리드 검색, 캐시, 비용 최적화
6. 보안/운영: 키 관리, 에러 처리, WebSocket/프록시 이슈 대응
7. 질의응답

## 6) 장애 대비 플랜
- WebSocket 불가 시: 사전 캡처한 스크린샷/짧은 영상 재생
- Azure 한도/오류 시: 이미 인덱싱된 저장소로 데모 전환 또는 검색만 시연
- 네트워크 지연 시: "인덱스 통계" / "README 보여줘" 등 빠른 응답 위주로 진행

## 7) 시간 배분(7~10분)
- 1분: 문제/해결
- 2분: 아키텍처
- 3~5분: 데모
- 1~2분: Q&A

---
TIP: 발표 전/중 실시간 모니터링은 브라우저 개발자도구(Network)와 서버 로그를 나란히 띄워두세요.
