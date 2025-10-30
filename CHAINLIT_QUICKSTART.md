# Chainlit 채팅앱 - 빠른 실행

## 즉시 실행
```bash
cd C:\Users\User\IdeaProjects\git_history_gen
chainlit run src/chat_app.py
```

## 예시 질문
```
최근 커밋 요약해줘
버그 수정 커밋 찾아줘
README 보여줘
abc123 커밋 diff 보여줘
```

## 체크리스트
- [x] src/chat_app.py 실행 가능
- [x] .env에 Azure 설정 완료
- [x] 브라우저 접속 확인(8000)

## 트러블슈팅
- 포트 사용 중 → `--port 8080`
- chainlit 없음 → `pip install chainlit` 또는 `uv pip install chainlit`
