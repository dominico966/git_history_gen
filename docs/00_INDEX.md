# Git History Generator - 문서 인덱스

이 문서는 프로젝트의 모든 문서를 체계적으로 정리한 인덱스입니다.

## 📚 주요 문서

### 1. 사용자 가이드
- **[USER_GUIDE.md](USER_GUIDE.md)** - 전체 기능 사용 가이드
- **[AZURE_SEARCH_INDEX_GUIDE.md](AZURE_SEARCH_INDEX_GUIDE.md)** - Azure AI Search Index 활용 가이드 🆕

### 2. 프로젝트 평가
- **[PROJECT_GUIDE_COMPLIANCE_REPORT.md](PROJECT_GUIDE_COMPLIANCE_REPORT.md)** - 프로젝트 가이드 준수 평가 (95% 준수)
- **[PROJECT_EVALUATION.md](PROJECT_EVALUATION.md)** - 프로젝트 종합 평가
- **[FINAL_COMPLETION_REPORT.md](FINAL_COMPLETION_REPORT.md)** - 최종 완성 보고서

### 3. 채팅앱 가이드
- **[CHAT_APP_GUIDE_NEW.md](CHAT_APP_GUIDE_NEW.md)** - Chainlit 채팅앱 최신 가이드 (권장)
- ~~[CHAT_APP_GUIDE.md](CHAT_APP_GUIDE.md)~~ - 구버전 (참고용)

## 🔧 기술 문서

### 아키텍처 & 구현
- **[PROJECT_IMPLEMENTATION.md](PROJECT_IMPLEMENTATION.md)** - 프로젝트 구현 상세 문서
- **[MULTI_REPO_INDEXING_SUMMARY.md](MULTI_REPO_INDEXING_SUMMARY.md)** - 다중 저장소 인덱싱 기능
- **[COST_OPTIMIZATION.md](COST_OPTIMIZATION.md)** - 비용 최적화 전략

### 도구 및 기능
- **[ONLINE_READER_TOOLS.md](ONLINE_READER_TOOLS.md)** - 온라인 파일 읽기 도구
- **[GITHUB_SEARCH_TOOL.md](GITHUB_SEARCH_TOOL.md)** - GitHub 저장소 검색 도구
- **[CACHE_AND_CONTEXT_IMPROVEMENT.md](CACHE_AND_CONTEXT_IMPROVEMENT.md)** - 캐시 및 컨텍스트 개선

## 🐛 문제 해결 (해결 완료)

아래 문서들은 개발 중 발생한 문제와 해결 방법을 기록한 것입니다. **모두 해결 완료**되었습니다.

### Function Calling 관련
- **[FUNCTION_CALLING_FIX.md](FUNCTION_CALLING_FIX.md)** - Function Calling 400 에러 해결
- **[TOOL_CALL_LOOP_FIX.md](TOOL_CALL_LOOP_FIX.md)** - 도구 호출 무한 루프 해결

### 응답 및 타임아웃 관련
- **[STREAMING_RESPONSE_FIX.md](STREAMING_RESPONSE_FIX.md)** - 스트리밍 응답 구현
- **[CHAT_TIMEOUT_FIX.md](CHAT_TIMEOUT_FIX.md)** - 채팅 타임아웃 해결
- **[CONVERSATION_TIMEOUT_FIX.md](CONVERSATION_TIMEOUT_FIX.md)** - 대화 타임아웃 해결
- **[CHAT_PROGRESS_UPDATE_FIX.md](CHAT_PROGRESS_UPDATE_FIX.md)** - 진행 상황 업데이트 개선
- **[CHAT_APP_COMPLETE_FIX.md](CHAT_APP_COMPLETE_FIX.md)** - 채팅앱 완전 수정

### 인덱싱 및 시스템 관련
- **[INDEXING_RESULT_FIX.md](INDEXING_RESULT_FIX.md)** - 인덱싱 결과 해석 개선
- **[WINDOWS_LONG_PATH_FIX.md](WINDOWS_LONG_PATH_FIX.md)** - Windows 긴 경로 문제 해결

### 기타
- **[MULTI_REPO_INDEXING.md](MULTI_REPO_INDEXING.md)** - 다중 저장소 인덱싱 문제 해결

## 📊 테스트 보고서

- **[TEST_REPORT.md](TEST_REPORT.md)** - 초기 테스트 보고서
- **[TEST_REPORT_MULTI_REPO.md](TEST_REPORT_MULTI_REPO.md)** - 다중 저장소 테스트 보고서
- **[FUNCTIONALITY_TEST_FINAL.md](FUNCTIONALITY_TEST_FINAL.md)** - 최종 기능 테스트
- **[FUNCTIONALITY_TEST_FIX.md](FUNCTIONALITY_TEST_FIX.md)** - 기능 테스트 수정

## 📝 업데이트 로그

- **[UPDATE_SUMMARY.md](UPDATE_SUMMARY.md)** - 업데이트 요약
- **[UPDATE_REPORT.md](UPDATE_REPORT.md)** - 업데이트 보고서
- **[UPDATE_MULTI_REPO.md](UPDATE_MULTI_REPO.md)** - 다중 저장소 업데이트

## 🎯 프로젝트 현황 요약

### ✅ 구현 완료된 주요 기능
1. **다중 저장소 인덱싱** - 여러 저장소를 하나의 인덱스에서 관리
2. **LLM Function Calling** - 12개 도구를 자연어로 호출
3. **하이브리드 검색** - 텍스트 + 벡터 검색
4. **온라인 파일 읽기** - GitHub 파일 직접 읽기
5. **스트리밍 응답** - 실시간 답변 생성
6. **캐시 시스템** - 저장소 복제 캐싱으로 속도 개선
7. **비용 최적화** - 토큰 사용량 제한 및 배치 처리

### ✅ 테스트 현황
- **전체 테스트**: 59개
- **통과**: 58개
- **실패**: 1개 (test_imports - 사소한 테스트 함수 이름 문제)

### ✅ AI 지침 준수율
- **95%** (11개 중 10개 완전 준수)

## 📂 문서 카테고리 설명

### 사용자 문서
일반 사용자가 프로젝트를 사용하는 방법을 설명합니다.

### 기술 문서
개발자를 위한 구현 상세 내용과 아키텍처를 설명합니다.

### 문제 해결 문서
개발 중 발생한 문제와 해결 과정을 기록합니다. (모두 해결 완료)

### 테스트 문서
테스트 결과와 품질 보증 활동을 기록합니다.

---

**최종 업데이트**: 2025-10-28  
**문서 버전**: 1.0  
**프로젝트 상태**: ✅ 완성 (95% 가이드 준수)

