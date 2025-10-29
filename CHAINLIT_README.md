# Git History Generator - Chainlit 채팅앱 🤖

Git 저장소의 커밋 히스토리를 분석하고 검색할 수 있는 대화형 AI 어시스턴트입니다.

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# 필수 환경변수 설정
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
```

### 2. 실행

```bash
# Chainlit 앱 실행
chainlit run src/chat_app.py

# 브라우저에서 http://localhost:8000 접속
```

## 📖 사용 방법

### 명령어 모드

```
/index .                    # 현재 디렉토리 인덱싱
/summary . 50              # 최근 50개 커밋 요약
/search 버그 수정           # 커밋 검색
/contributors . 500        # 기여자 분석
/bugs . 200                # 버그 커밋 찾기
/help                      # 도움말
```

### 자연어 모드

```
"최근 커밋들을 요약해줘"
"버그 수정 관련 커밋을 찾아줘"
"누가 가장 많이 기여했어?"
```

## ✨ 주요 기능

- 🔍 **하이브리드 검색**: 텍스트 + 벡터 검색
- 📊 **AI 기반 요약**: LLM이 커밋 히스토리 분석
- 👥 **기여자 분석**: 기여도 순위 및 통계
- 🐛 **버그 추적**: 버그 관련 커밋 자동 탐지
- 💬 **자연어 대화**: 명령어 없이 질문 가능
- 🔄 **세션 관리**: 저장소 경로 자동 기억

## 📚 상세 문서

- [채팅앱 가이드](docs/CHAT_APP_GUIDE.md)
- [사용자 가이드](docs/USER_GUIDE.md)
- [프로젝트 가이드 준수 평가](docs/PROJECT_GUIDE_COMPLIANCE_REPORT.md)

## 🧪 테스트

```bash
# 전체 테스트
pytest tests/test_chat_app.py -v

# 특정 테스트
pytest tests/test_chat_app.py::test_command_parsing -v
```

## 🛠️ 기술 스택

- **UI**: Chainlit
- **AI**: Azure OpenAI (GPT-4, Embeddings)
- **검색**: Azure AI Search
- **Git**: GitPython
- **언어**: Python 3.13+

## 📄 라이선스

MIT License

