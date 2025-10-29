# Git History Generator

Git 저장소의 커밋 히스토리를 분석하고 검색하는 AI 기반 도구입니다.

## 🌟 주요 기능

- **커밋 요약**: LLM을 활용한 지능형 커밋 히스토리 분석
- **자연어 검색**: 벡터 + 텍스트 하이브리드 검색
- **기여자 분석**: 기여자별 활동 통계 및 평가
- **버그 추적**: 버그 관련 커밋 자동 식별
- **대화형 UI**: Streamlit 기반 웹 인터페이스
- **🆕 커밋 간 변경사항 문맥**: 커밋 간의 관계와 영향 범위 자동 분석
- **🆕 함수/클래스 추적**: 수정/추가/삭제된 함수와 클래스 자동 감지
- **🆕 코드 복잡도 분석**: 변경 사항의 복잡도 자동 평가

## 🔧 기술 스택

- **Python 3.13+**
- **Azure OpenAI**: GPT-4o-mini, text-embedding-3-small
- **Azure AI Search**: 벡터 검색
- **GitPython**: Git 저장소 분석
- **Streamlit**: 웹 UI

## 📦 설치

```bash
# 의존성 설치
uv sync

# 또는 pip 사용
pip install -r requirements.txt
```

## ⚙️ 환경 설정

`.env` 파일을 생성하고 다음 환경변수를 설정하세요:

```bash
# .env.example 파일을 복사
cp .env.example .env

# 환경변수 편집
# Azure OpenAI 및 Azure AI Search 키를 입력하세요
```

필수 환경변수:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_MODEL` (기본값: gpt-4.1-mini)
- `AZURE_OPENAI_EMBEDDING_MODEL` (기본값: text-embedding-3-small)
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

## 🚀 실행

```bash
# Streamlit 앱 실행
streamlit run src/app.py
```

브라우저에서 `http://localhost:8501`로 접속하세요.

## 📖 사용 방법

### 1. 인덱싱

1. 사이드바에서 Git 저장소 경로 입력
2. "Index Repository" 버튼 클릭
3. 커밋 데이터가 Azure AI Search에 인덱싱됨

### 2. 커밋 요약

1. "Commit Summary" 탭 선택
2. 분석할 커밋 수 조정
3. "Generate Summary" 클릭
4. LLM이 생성한 요약 확인

### 3. 커밋 검색

1. "Search Commits" 탭 선택
2. 자연어로 검색 쿼리 입력 (예: "로그인 버그 수정")
3. "Search" 클릭
4. 관련 커밋 결과 확인
5. **🆕 각 결과에서 확인 가능한 정보:**
   - 변경 문맥: 커밋의 전반적인 변경 요약
   - 수정된 함수: 변경된 함수 목록
   - 수정된 클래스: 변경된 클래스 목록
   - 코드 복잡도: low/medium/high
   - 커밋 관계: 이전 커밋과의 관계 (related_work, same_area, independent)

### 4. 기여자 분석

1. "Contributors Analysis" 탭 선택
2. 평가 기준 입력 (선택사항)
3. "Analyze" 클릭
4. 기여자별 통계 확인

### 5. 버그 커밋 찾기

1. "Bug Commits" 탭 선택
2. "Find Bugs" 클릭
3. 버그 관련 커밋 목록 확인

## 🧪 테스트

```bash
# 모든 테스트 실행
pytest tests/ -v

# 특정 테스트 실행
pytest tests/test_embedding.py -v
```

## 📁 프로젝트 구조

```
src/
├── agent.py              # Azure 클라이언트 초기화
├── app.py                # Streamlit 웹 애플리케이션
├── document_generator.py # Git 커밋 추출
├── embedding.py          # 텍스트 임베딩
├── indexer.py            # Azure AI Search 인덱싱
└── tools.py              # 도구 함수들

tests/
├── test_document_generator.py
├── test_embedding.py
└── test_tools.py

docs/
├── PROJECT_IMPLEMENTATION.md  # 구현 문서
└── PROJECT_EVALUATION.md      # 평가 보고서
```

## 🎯 성능 최적화

- **배치 처리**: 임베딩 API 호출을 배치로 처리 (기본 20개)
- **비동기 처리**: I/O 대기 시간 최소화
- **캐싱**: Streamlit 리소스 캐싱으로 재계산 방지
- **프롬프트 최적화**: 토큰 사용 최소화

환경변수 `EMBEDDING_BATCH_SIZE`로 배치 크기를 조정할 수 있습니다.

## 📝 개발 가이드

자세한 개발 가이드는 다음 문서를 참조하세요:
- [프로젝트 구현 문서](docs/PROJECT_IMPLEMENTATION.md)
- [프로젝트 평가 보고서](docs/PROJECT_EVALUATION.md)
- [프로젝트 가이드](project_guide.md)

## 🤝 기여

이 프로젝트는 `project_guide.md`의 지침에 따라 작성되었습니다.

## 📄 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

