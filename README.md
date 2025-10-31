# Git History Generator 🤖

[![Tests](https://img.shields.io/badge/tests-100%25%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.13%2B-blue)]()

[//]: # (License 문서가 현재 리포지토리에 없으므로 링크를 비활성화합니다)

Git 저장소의 커밋 히스토리를 AI로 분석하는 대화형 도구입니다.

- 🎬 라이브 데모(발표): https://ktds-edu.ddns.dominico966.net/

## ✨ 주요 기능

- 🔍 **자연어 검색**: "버그 수정 커밋 찾아줘" → AI가 자동으로 검색
- 📊 **커밋 요약**: LLM이 최근 변경사항을 분석하고 요약
- 👥 **기여자 분석**: 누가 어떤 작업을 얼마나 했는지 통계
- 🐛 **버그 추적**: 버그 관련 커밋 자동 탐지
- 🌐 **GitHub 통합**: URL만으로 저장소 분석 가능
- 💬 **대화형 UI**: Chainlit 기반 채팅 인터페이스
- ⚡ **하이브리드 검색**: 텍스트 + 벡터 검색 결합

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 복제
git clone https://github.com/dominico966/git_history_gen.git
cd git_history_gen

# 의존성 설치
uv sync
# 또는
pip install -r requirements.txt
```

### 2. 환경 설정

`.env` 파일을 생성하고 Azure 키를 설정하세요:

```bash
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_MODEL=gpt-4.1-mini
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=git-commits
```

### 3. 실행

```bash
chainlit run src/chat_app.py
```

브라우저에서 `http://localhost:8000` 접속!

## 📖 사용 예시

### 자연어로 질문하기

```
"최근 커밋 요약해줘"
"인증 관련 버그 수정 커밋 찾아줘"
"누가 가장 많이 기여했어?"
"README 파일 보여줘"
```

### GitHub 저장소 분석

```
User: "타우리 프로젝트 분석해줘"

AI: 🔧 search_github_repo 실행 중...
    ✅ 'tauri-apps/tauri' 발견 (⭐ 85,234)
    
    🔧 set_current_repository 실행 중...
    ✅ 저장소 설정 완료
    
    🔧 get_readme 실행 중...
    ✅ README 읽기 완료
    
    🔧 index_repository 실행 중...
    📊 50개 커밋 인덱싱 중...
    ✅ 인덱싱 완료
    
    💭 답변 생성 중...
    
    Tauri는 Rust로 작성된 크로스 플랫폼 데스크톱 앱 
    프레임워크입니다. 최근 주요 변경사항:
    ...
```

## 🏗️ 아키텍처

```
Chainlit UI → Agent → Tools → Document Generator → Azure Services
                 ↓              ↓                      ↓
          Function Calling   Git 분석          [OpenAI + AI Search]
```

## 🔧 기술 스택

- **Python 3.13+**
- **Azure OpenAI** (GPT-4.1-mini, text-embedding-3-small)
- **Azure AI Search** (하이브리드 벡터 검색)
- **Chainlit** (대화형 UI)
- **GitPython** (Git 저장소 분석)
- **pytest** (테스트 프레임워크)

## 📊 프로젝트 현황

- ✅ **59개 테스트 모두 통과** (100%) 🎉
- ✅ **18개 도구 완전 구현**
  - 저장소/인덱스 관리 포함
  - 커밋 분석/검색 전체 커버
  - 온라인 읽기 도구 포함
- ✅ **프로젝트 가이드 95% 준수**
- ✅ **비용 최적화 완료**
- ✅ **문서화 완료**

## 🛠️ 사용 가능한 도구 (18개)

### 저장소/검색/설정

1. set_current_repository — 현재 저장소 설정
2. get_commit_count — 저장소 커밋 개수(기간 필터 지원)
3. search_github_repo — GitHub 저장소 검색

### 커밋 분석/검색

4. get_commit_summary — LLM 기반 요약
5. search_commits — 하이브리드 검색 (텍스트 + 벡터)
6. analyze_contributors — 기여자 분석
7. find_bug_commits — 버그 커밋 탐지
8. search_commits_by_date — 날짜 범위 커밋 검색

### 인덱스 관리

9. index_repository — 커밋 인덱싱 (Azure AI Search)
10. get_index_statistics — 인덱스 통계 정보
11. list_indexed_repositories — 인덱싱된 저장소 목록
12. get_repository_info — 특정 저장소 상세 정보
13. delete_repository_commits — 저장소 커밋 문서 삭제
14. check_index_health — 인덱스 상태 확인

### 온라인 읽기

15. get_readme — README 읽기
16. read_file_from_commit — 특정 커밋 파일 읽기
17. get_file_context — 파일 diff 및 컨텍스트
18. get_commit_diff — 커밋 전체 diff

*참고: 실제 구현된 도구명은 `find_frequent_bug_commits`이며, 카테고리별로 기능적 그룹화하여 정리했습니다.*

## 📚 문서

### 시작하기
- [⚡ 빠른 실행 가이드](CHAINLIT_QUICKSTART.md)
- [🗄️ Azure AI Search Index 활용 가이드](docs/AZURE_SEARCH_INDEX_GUIDE.md)

[//]: # (### 프로젝트 정보)

[//]: # (- [🗂️ 발표 체크리스트]&#40;docs/PRESENTATION_CHECKLIST.md&#41;)

[//]: # (- [🎬 데모 스크립트]&#40;docs/DEMO_SCRIPT.md&#41;)

[//]: # (- [❓ Q&A 예상 질문]&#40;docs/QNA.md&#41;)

[//]: # (- [🏁 평가 대응 브리프]&#40;docs/EVALUATION_BRIEF.md&#41;)

### 기술 문서
- [🔧 온라인 읽기 도구](docs/ONLINE_READER_TOOLS.md)
- [🧵 비동기/스트리밍 UI 분리](docs/ASYNC_UI_SEPARATION.md)

## 🧪 테스트

```bash
# 전체 테스트 실행 (59개 모두 통과!)
pytest tests/ -v

# 특정 테스트
pytest tests/test_chat_app.py -v
pytest tests/test_functionality.py -v

# 커버리지 확인
pytest tests/ --cov=src --cov-report=html
```

## 💡 핵심 기능 상세

### 1. Function Calling
LLM이 자동으로 적절한 도구를 선택하고 실행합니다.

```python
# 사용자: "최근 커밋 요약해줘"
# → LLM이 get_commit_summary 도구 자동 선택
# → repo_path=".", limit=50 파라미터 추출
# → 도구 실행 후 결과 분석
```

### 2. 하이브리드 검색
텍스트 검색(BM25)과 벡터 검색을 결합하여 정확도 향상

```python
# Azure AI Search Hybrid Search
# - Text: "bug fix authentication"
# - Vector: [0.123, -0.456, ...] (1536 dimensions)
# → 관련도 높은 커밋 반환
```

### 3. 인덱스 관리

Azure AI Search를 활용한 커밋 데이터 관리

```python
# 저장소 인덱싱
"저장소 인덱싱해줘: https://github.com/user/repo"
# → 커밋 데이터를 Azure AI Search에 저장

# 인덱스 통계 확인
"인덱스 통계 보여줘"
# → 총 커밋 수, 저장소 수, 기여자 수 등

# 인덱싱된 저장소 목록
"인덱싱된 저장소 목록 보여줘"
# → 각 저장소의 커밋 수와 정보

# 특정 저장소 상세 정보
"저장소 정보 보여줘: repo_id"
# → 커밋 수, 기여자 수, 날짜 범위 등

# 인덱스 상태 확인
"인덱스 상태 확인해줘"
# → 인덱스가 정상 작동하는지 검증
```

**예제 스크립트 실행**:

```bash
python examples/index_usage_examples.py
```

9가지 실용 예제 포함:

- 기본 인덱싱
- 인덱스 통계 확인
- 다중 저장소 관리
- 증분 인덱싱
- 날짜 범위 인덱싱

### 3. 스트리밍 응답

ChatGPT처럼 실시간으로 답변 생성

```python
# 답변이 한 글자씩 실시간 표시
"Tauri는..." → "Tauri는 Rust로..." → "Tauri는 Rust로 작성된..."
```

### 4. 저장소 캐시

원격 저장소를 한 번만 복제하여 속도 개선

```python
# 첫 실행: git clone (느림)
# 이후 실행: git pull (빠름)
```

## 🔥 성능 최적화

- **배치 임베딩**: 20개씩 묶어서 처리
- **비동기 처리**: asyncio 활용
- **토큰 제한**: 최대 커밋 200개, 검색 결과 20개
- **메시지 히스토리**: 최근 8개만 유지
- **증분 인덱싱**: 새 커밋만 추가

[//]: # (## 🤝 기여)

[//]: # ()
[//]: # (이슈와 PR을 환영합니다!)

[//]: # ()
[//]: # (1. Fork the Project)

[//]: # (2. Create your Feature Branch &#40;`git checkout -b feature/AmazingFeature`&#41;)

[//]: # (3. Commit your Changes &#40;`git commit -m 'Add some AmazingFeature'`&#41;)

[//]: # (4. Push to the Branch &#40;`git push origin feature/AmazingFeature`&#41;)

[//]: # (5. Open a Pull Request)

[//]: # (## 📄 라이선스)

[//]: # (라이선스 문서를 추가하면 여기 링크를 활성화하세요)

[//]: # (## 🧩 운영&#40;프로덕션&#41; 참고: "읽어보기" 버튼만 보일 때)

[//]: # (- 대부분 WebSocket 미업그레이드&#40;프록시 설정 누락&#41; or 환경변수 미설정으로 on_chat_start 초기화 실패일 때 발생합니다.)

[//]: # (- 체크리스트)

[//]: # (  - 프록시에서 WebSocket 업그레이드 허용&#40;Upgrade/Connection 헤더, 타임아웃/버퍼 크기&#41;)

[//]: # (  - 체인릿 루트 경로 사용 시 서버 루트 경로 설정&#40;root_path&#41; 일치 여부)

[//]: # (  - AZURE_OPENAI/SEARCH 관련 환경변수 값 유효성 확인&#40;엔드포인트/키/인덱스명&#41;)

[//]: # (  - 브라우저 콘솔/네트워크 탭에서 /ws 연결 상태, 401/403/404 에러 존재 여부)

[//]: # ()

[//]: # (---)

**제작**: AI Agent with GitHub Copilot  
**최종 업데이트**: 2025-10-30  
**프로젝트 상태**: ✅ Production Ready
