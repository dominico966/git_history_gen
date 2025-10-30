# Git History Generator - Chainlit 앱

## 실행
```bash
# .env 준비 후
chainlit run src/chat_app.py
```
- 브라우저: http://localhost:8000

## 사용 예시
명령어 모드
```
/index .             # 현재 디렉토리 인덱싱
/summary . 50        # 최근 50개 커밋 요약
/search 버그 수정     # 커밋 검색
/contributors . 500  # 기여자 분석
/bugs . 200          # 버그 커밋 찾기
```

자연어 모드
```
최근 커밋들을 요약해줘
버그 수정 관련 커밋을 찾아줘
누가 가장 많이 기여했어?
```

## 팁
- 긴 작업은 자동으로 비동기 실행, 진행 상황은 Step으로 표시
- 대용량 인덱싱은 자동 분할/배치 처리
- 결과가 길면 UI/LLM 한도 내에서 자동 요약
