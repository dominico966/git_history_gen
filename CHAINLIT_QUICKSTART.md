# Chainlit 채팅앱 - 빠른 실행 가이드

## 🚀 즉시 실행하기

```bash
# 1. 프로젝트 루트로 이동
cd C:\Users\User\IdeaProjects\git_history_gen

# 2. Chainlit 앱 실행
chainlit run src/chat_app.py

# 3. 브라우저에서 자동으로 http://localhost:8000 접속
```

## 📝 사용 예시

### 명령어 모드

```
/help                          # 도움말
/index .                       # 현재 디렉토리 인덱싱
/summary . 50                  # 최근 50개 커밋 요약
/search 버그 수정               # 커밋 검색
/contributors . 500            # 기여자 분석
/bugs . 200                    # 버그 커밋 찾기
```

### 자연어 모드

```
최근 커밋들을 요약해줘
버그 수정 관련 커밋을 찾아줘
누가 가장 많이 기여했어?
인증 관련 코드를 수정한 커밋은?
```

## ✨ 주요 기능

- ✅ **6개 명령어**: index, summary, search, contributors, bugs, help
- ✅ **자연어 지원**: 인텐트 기반 자동 분류
- ✅ **세션 관리**: 저장소 경로 자동 저장
- ✅ **스트리밍 응답**: 실시간 결과 표시
- ✅ **에러 처리**: 사용자 친화적 에러 메시지

## 📋 체크리스트

- [x] `src/chat_app.py` 구현 완료
- [x] `tests/test_chat_app.py` 테스트 파일 작성
- [x] `docs/CHAT_APP_GUIDE.md` 상세 가이드 작성
- [x] `.chainlit` 설정 파일 생성
- [x] `CHAINLIT_README.md` 실행 가이드 작성
- [x] 모든 에러 수정 완료

## 🎯 구현된 기능 요약

### 1. 명령어 처리
- `/index` - CommitIndexer 사용하여 저장소 인덱싱
- `/summary` - tools.get_commit_summary 호출
- `/search` - tools.search_commits 호출 (하이브리드 검색)
- `/contributors` - tools.analyze_contributors 호출
- `/bugs` - tools.find_frequent_bug_commits 호출
- `/help` - 도움말 표시

### 2. 자연어 처리
- 키워드 기반 인텐트 분류
- LLM을 통한 고급 질문 분석
- 자동 명령어 매핑

### 3. 세션 관리
- `repo_path` - 마지막 사용 저장소 경로
- `index_name` - Azure Search 인덱스 이름

### 4. 비동기 처리
- `asyncio.get_event_loop().run_in_executor` 사용
- 블로킹 작업을 별도 스레드에서 실행
- UI 반응성 유지

### 5. 스트리밍 응답
- `msg.stream_token()` 사용
- 실시간 진행 상황 표시
- 사용자 경험 개선

## 🔧 트러블슈팅

### 문제: "Failed to initialize clients"
**해결:** `.env` 파일의 Azure 환경변수 확인

### 문제: 포트 8000 이미 사용 중
**해결:** `chainlit run src/chat_app.py --port 8080`

### 문제: chainlit 명령어를 찾을 수 없음
**해결:** `uv pip install chainlit` 또는 `pip install chainlit`

## 📚 추가 문서

- 상세 가이드: `docs/CHAT_APP_GUIDE.md`
- 프로젝트 평가: `docs/PROJECT_GUIDE_COMPLIANCE_REPORT.md`
- 사용자 가이드: `docs/USER_GUIDE.md`

## 🎉 완료!

Chainlit 채팅앱이 성공적으로 구현되었습니다.
`chainlit run src/chat_app.py` 명령어로 즉시 실행하세요!

