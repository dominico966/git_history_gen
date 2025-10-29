"""
Azure AI Search Index 빠른 시작 가이드
콘솔에서 실행하면 주요 기능을 확인할 수 있습니다.
"""


def print_guide():
    """가이드 출력"""
    guide = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   🗄️  Azure AI Search Index 활용 가이드                         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

📚 현재 앱에서 Azure AI Search Index를 활용하는 방법:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 1. 기본 사용법 (채팅 앱)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  저장소 인덱싱
    💬 "저장소 인덱싱해줘: https://github.com/user/repo"
    💬 "최근 100개 커밋만 인덱싱해줘"
    💬 "2024년 커밋만 인덱싱해줘"

2️⃣  커밋 검색
    💬 "로그인 기능 관련 커밋 찾아줘"
    💬 "버그 수정 커밋 검색"
    💬 "performance improvement 관련 변경사항"

3️⃣  인덱스 관리
    💬 "인덱스 통계 보여줘"
    💬 "인덱싱된 저장소 목록"
    💬 "인덱스 상태 확인해줘"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 2. 사용 가능한 도구 (18개)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 인덱싱 관련:
  ✅ index_repository          - 저장소 인덱싱
  ✅ set_current_repository    - 현재 저장소 설정

🔍 검색 관련:
  ✅ search_commits            - 하이브리드 검색 (텍스트 + 벡터)
  ✅ get_commit_summary        - LLM 기반 커밋 요약
  ✅ analyze_contributors      - 기여자 분석
  ✅ find_bug_commits          - 버그 커밋 탐지

📊 인덱스 관리 (NEW! 🆕):
  ✅ get_index_statistics      - 인덱스 통계 정보
  ✅ list_indexed_repositories - 인덱싱된 저장소 목록
  ✅ get_repository_info       - 특정 저장소 상세 정보
  ✅ delete_repository_commits - 저장소 삭제
  ✅ check_index_health        - 인덱스 상태 확인

📖 파일 읽기:
  ✅ read_file_from_commit     - 특정 커밋의 파일 내용
  ✅ get_file_context          - 파일 변경 컨텍스트
  ✅ get_commit_diff           - 커밋 전체 diff
  ✅ get_readme                - README 내용
  ✅ search_github_repo        - GitHub 저장소 검색

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 3. 실전 시나리오
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 시나리오 1: 신규 프로젝트 분석
   1. "저장소 인덱싱해줘: https://github.com/microsoft/playwright"
   2. "README 보여줘"
   3. "test automation 관련 커밋 찾아줘"
   4. "기여자 분석해줘"

📌 시나리오 2: 특정 기능 개발 히스토리
   1. "현재 저장소 설정: https://github.com/mycompany/app"
   2. "저장소 인덱싱 (전체)"
   3. "authentication 관련 커밋 검색 (top 20)"
   4. "각 커밋의 diff 확인"

📌 시나리오 3: 다중 저장소 비교
   1. "React 저장소 인덱싱"
   2. "Vue 저장소 인덱싱"
   3. "hooks implementation 통합 검색"
   4. "각 저장소별 구현 방식 비교"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ 4. 빠른 시작
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 환경 설정 (.env):
   AZURE_OPENAI_API_KEY=your-api-key
   AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
   AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
   AZURE_SEARCH_API_KEY=your-search-api-key
   AZURE_SEARCH_INDEX_NAME=git-commits

🚀 채팅 앱 실행:
   $ chainlit run src/chat_app.py

📦 예제 스크립트 실행:
   $ python examples/index_usage_examples.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 5. 상세 문서
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 docs/AZURE_SEARCH_INDEX_GUIDE.md
   - 상세한 활용 가이드
   - 고급 기능 설명
   - 최적화 팁
   - 문제 해결

📖 examples/README.md
   - 빠른 시작 가이드
   - 실전 예제
   - 명령어 레퍼런스

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 6. 핵심 기능
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ 하이브리드 검색 (텍스트 + 벡터)
   - BM25 텍스트 검색과 임베딩 벡터 검색 결합
   - 의미적 유사성과 키워드 매칭 동시 지원

✨ 증분 인덱싱
   - 이미 인덱싱된 커밋 건너뛰기 (skip_existing=True)
   - 새로운 커밋만 효율적으로 추가

✨ 다중 저장소 지원
   - 여러 저장소를 하나의 인덱스에서 관리
   - 통합 검색 및 개별 저장소 필터링

✨ 인덱스 통계 및 관리
   - 실시간 통계 조회 (커밋 수, 저장소 수, 기여자 수)
   - 인덱스 상태 확인 및 건강도 체크
   - 저장소별 관리 (조회, 삭제)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 7. 최적화 설정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

환경 변수로 제한 설정:
   MAX_COMMIT_LIMIT=200        # 최대 커밋 제한
   MAX_SEARCH_TOP=20           # 최대 검색 결과
   MAX_CONTRIBUTOR_LIMIT=500   # 기여자 분석 제한

권장 사항:
   ✅ 처음에는 제한된 개수로 시작 (limit=100)
   ✅ 증분 인덱싱 활용 (skip_existing=True)
   ✅ 필요한 날짜 범위만 인덱싱
   ✅ 특정 저장소로 검색 필터링

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 8. 참고 링크
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📘 Azure AI Search 문서:
   https://learn.microsoft.com/azure/search/

📘 Vector Search 가이드:
   https://learn.microsoft.com/azure/search/vector-search-overview

📘 OpenAI Embeddings:
   https://platform.openai.com/docs/guides/embeddings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ 지금 바로 시작하세요!

   $ chainlit run src/chat_app.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(guide)


if __name__ == "__main__":
    print_guide()

