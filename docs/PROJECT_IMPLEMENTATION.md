# Git History Generator - 프로젝트 문서

## 📋 프로젝트 개요

Git 저장소의 커밋 히스토리를 분석하고 검색하는 AI 기반 도구입니다. Azure OpenAI와 Azure AI Search를 활용하여 자연어로 커밋을 검색하고, 기여자 분석, 버그 추적 등의 기능을 제공합니다.

## 🏗️ 아키텍처

### 주요 컴포넌트

1. **Document Generator** (`document_generator.py`)
   - GitPython을 사용하여 커밋 히스토리 추출
   - 파일 변경 통계 계산
   - 비동기 지원

2. **Embedding Module** (`embedding.py`)
   - Azure OpenAI를 사용한 텍스트 임베딩
   - 배치 처리로 API 호출 최소화
   - 동기/비동기 버전 모두 지원

3. **Indexer** (`indexer.py`)
   - Azure AI Search 인덱스 생성 및 관리
   - 커밋 데이터 인덱싱
   - 벡터 검색 지원

4. **Tools** (`tools.py`)
   - 커밋 요약 (LLM 기반)
   - 자연어 검색 (하이브리드: 텍스트 + 벡터)
   - 기여자 분석
   - 버그 커밋 추적

5. **Agent** (`agent.py`)
   - Azure 클라이언트 초기화
   - 환경변수 검증

6. **Web Application** (`app.py`)
   - Streamlit 기반 대화형 UI
   - 4개의 주요 탭:
     - 커밋 요약
     - 커밋 검색
     - 기여자 분석
     - 버그 커밋

## 🎯 주요 기능

### 1. 커밋 요약
- LLM을 활용한 지능형 요약
- 최근 변경사항, 주요 트렌드 분석
- 기여자 활동 패턴 파악

### 2. 자연어 검색
- 벡터 검색 + 텍스트 검색 하이브리드
- 의미론적 유사도 기반 검색
- 관련성 점수 제공

### 3. 기여자 분석
- 커밋 수, 변경 라인 수, 파일 변경 빈도 분석
- 사용자 정의 평가 기준 지원
- 최근 활동 추적

### 4. 버그 추적
- 버그 관련 커밋 자동 식별
- 버그 발생 빈도 분석
- 패턴 인식

## 🔧 기술 스택

- **언어**: Python 3.13+
- **주요 라이브러리**:
  - GitPython: Git 저장소 분석
  - Azure SDK: Azure 서비스 통합
  - OpenAI: LLM 및 임베딩
  - Streamlit: 웹 UI
  - pytest: 테스트

- **Azure 서비스**:
  - Azure OpenAI: GPT-4, text-embedding-ada-002
  - Azure AI Search: 벡터 검색 및 인덱싱

## 📦 설치 및 실행

### 1. 환경 설정

```bash
# 의존성 설치
uv sync

# 환경변수 설정 (.env 파일 생성)
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

AZURE_SEARCH_ENDPOINT=your_search_endpoint
AZURE_SEARCH_API_KEY=your_search_key
AZURE_SEARCH_INDEX_NAME=git-commits

EMBEDDING_BATCH_SIZE=20
```

### 2. 애플리케이션 실행

```bash
streamlit run src/app.py
```

### 3. 테스트 실행

```bash
pytest tests/ -v
```

## 📊 성능 최적화

### CPU 자원 최소화
- 배치 처리로 API 호출 횟수 감소
- 비동기 처리로 I/O 대기 시간 최소화
- 캐싱을 통한 중복 계산 방지

### API 토큰 절약
- 임베딩 배치 크기 조정 가능 (기본 20개)
- LLM 호출 시 컨텍스트 최적화
- 프롬프트 엔지니어링으로 토큰 사용 최소화

## 🧪 테스트 커버리지

- `test_document_generator.py`: DocumentGenerator 기능 테스트
- `test_embedding.py`: 임베딩 함수 테스트
- `test_tools.py`: 도구 함수 테스트

모든 테스트는 Mock을 사용하여 외부 의존성 없이 실행 가능합니다.

## 📝 project_guide.md 준수사항

### ✅ 준수된 항목

1. **비동기/코루틴 활용**: embedding.py, document_generator.py에 비동기 함수 구현
2. **타입힌트**: 모든 함수에 완전한 타입힌트 제공
3. **예외처리**: try-except 블록으로 모든 주요 작업 보호
4. **로깅**: 모든 모듈에서 logging 사용
5. **테스트 코드**: tests 디렉토리에 포괄적인 테스트 작성
6. **기여자 분석**: analyze_contributors 함수로 구현
7. **사용자 정의 평가 기준**: contributor_criteria 매개변수 지원
8. **Azure 통합**: Azure OpenAI, Azure AI Search 완전 통합
9. **대화형 UI**: Streamlit으로 사용자 친화적 UI 구현
10. **Tool 형태 LLM 호출**: tools.py에 다양한 도구 함수 구현

### 📈 개선된 부분

1. **인덱싱 기능**: CommitIndexer 클래스로 완전한 인덱싱 워크플로우 구현
2. **하이브리드 검색**: 벡터 검색 + 텍스트 검색 결합
3. **프롬프트 최적화**: 구조화된 프롬프트로 LLM 응답 품질 향상
4. **UI/UX**: 4개 탭으로 기능 구분, 직관적인 인터페이스
5. **에러 핸들링**: 모든 작업에 대한 포괄적인 에러 처리
6. **문서화**: 모든 함수에 docstring 추가

## 🚀 향후 개선 방향

1. 증분 인덱싱 지원 (변경된 커밋만 재인덱싱)
2. 코드 리뷰 AI 어시스턴트 기능
3. 커밋 품질 자동 평가
4. 다양한 시각화 기능 추가
5. 멀티 저장소 동시 분석

## 📄 라이선스

이 프로젝트는 project_guide.md의 지침에 따라 작성되었습니다.

