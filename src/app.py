"""
Git History Generator - Streamlit Web Application
Git 저장소의 커밋 히스토리를 분석하고 검색하는 대화형 웹 애플리케이션
"""

import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent import initialize_models
from src.tools import (
    get_commit_summary,
    search_commits,
    analyze_contributors,
    find_frequent_bug_commits
)
from src.indexer import CommitIndexer
from src.repo_cache import RepoCloneCache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Git History Generator",
    page_icon="📚",
    layout="wide"
)

# Initialize models (cached)
@st.cache_resource
def get_clients():
    """클라이언트들을 초기화하고 캐싱합니다."""
    try:
        return initialize_models()
    except Exception as e:
        st.error(f"Failed to initialize clients: {e}")
        st.stop()

llm_client, search_client, index_client = get_clients()

# Main UI
st.title("📚 Git History Generator")
st.markdown("Git 저장소의 커밋 히스토리를 분석하고 검색하는 도구입니다.")

# Sidebar - Settings
with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("📁 Repository")
    repo_type = st.radio(
        "Repository Type",
        ["Local Path", "Remote URL"],
        help="로컬 저장소 또는 원격 저장소 선택"
    )

    if repo_type == "Local Path":
        repo_path = st.text_input(
            "Local Repository Path",
            value=".",
            help="분석할 로컬 Git 저장소의 경로를 입력하세요"
        )
    else:
        repo_path = st.text_input(
            "Remote Repository URL",
            value="",
            placeholder="https://github.com/username/repository",
            help="원격 Git 저장소 URL을 입력하세요 (예: https://github.com/rust-lang/rust)"
        )
        st.warning("⚠️ 원격 저장소는 임시로 clone됩니다. 큰 저장소는 시간이 걸릴 수 있습니다.")

    st.divider()

    st.subheader("기여자 평가 기준")
    contributor_criteria = st.text_area(
        "Contributor Evaluation Criteria",
        value="커밋 수, 변경 라인 수, 파일 변경 빈도",
        help="기여자를 평가할 기준을 입력하세요"
    )

    st.divider()

    # Index Management
    st.subheader("🔧 Index Management")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "git-commits")
    st.info(f"Current Index: `{index_name}`")

    # 인덱싱 옵션
    with st.expander("⚙️ Indexing Options", expanded=True):
        col_opt1, col_opt2 = st.columns(2)

        with col_opt1:
            commit_limit = st.number_input(
                "커밋 개수 제한",
                min_value=1,
                max_value=1000,
                value=10,
                step=10,
                help="인덱싱할 최대 커밋 수 (기본값: 10)"
            )

            skip_existing = st.checkbox(
                "증분 인덱싱 (기존 커밋 건너뛰기)",
                value=True,
                help="이미 인덱싱된 커밋은 건너뛰고 새로운 커밋만 추가합니다."
            )

        with col_opt2:
            use_date_filter = st.checkbox(
                "날짜 필터 사용",
                value=False,
                help="특정 기간의 커밋만 인덱싱합니다."
            )

            if use_date_filter:
                since_date = st.date_input(
                    "시작 날짜",
                    value=None,
                    help="이 날짜 이후의 커밋만 인덱싱"
                )
                until_date = st.date_input(
                    "종료 날짜",
                    value=None,
                    help="이 날짜 이전의 커밋만 인덱싱"
                )
            else:
                since_date = None
                until_date = None

        # 원격 저장소 경고
        if repo_type == "Remote URL":
            st.info("📦 원격 저장소는 전체 히스토리를 다운로드합니다 (shallow clone 없음)")

    # 비용 경고 표시
    if commit_limit > 100:
        st.warning(f"⚠️ {commit_limit}개 커밋 인덱싱 시 API 비용이 많이 발생할 수 있습니다!")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Index Repository", use_container_width=True):
            if not repo_path or (repo_type == "Remote URL" and not repo_path.startswith(('http://', 'https://', 'git@'))):
                st.error("올바른 저장소 경로 또는 URL을 입력하세요.")
            else:
                with st.spinner("Indexing commits..."):
                    try:
                        indexer = CommitIndexer(
                            search_client,
                            index_client,
                            llm_client,
                            index_name
                        )

                        # Create index if not exists
                        indexer.create_index_if_not_exists()

                        # Index repository with options
                        if repo_type == "Remote URL":
                            st.info(f"🔄 저장소 전체 히스토리를 다운로드합니다...")

                        # 날짜 변환
                        since_str = since_date.isoformat() if use_date_filter and since_date else None
                        until_str = until_date.isoformat() if use_date_filter and until_date else None

                        # 인덱싱 정보 표시
                        info_parts = [f"커밋 수: {commit_limit}"]
                        if since_str:
                            info_parts.append(f"시작: {since_str}")
                        if until_str:
                            info_parts.append(f"종료: {until_str}")
                        if skip_existing:
                            info_parts.append("증분 인덱싱")

                        st.info(f"📊 인덱싱 옵션: {', '.join(info_parts)}")

                        count = indexer.index_repository(
                            repo_path,
                            limit=commit_limit,
                            since=since_str,
                            until=until_str,
                            skip_existing=skip_existing
                        )
                        st.success(f"✓ Successfully indexed {count} commits!")

                    except Exception as e:
                        error_msg = str(e)

                        # 파일명이 너무 긴 경우 특별 처리
                        if 'Filename too long' in error_msg or '파일 경로가 너무 깁니다' in error_msg:
                            st.error("❌ 파일 경로가 너무 깁니다 (Windows 제한)")

                            with st.expander("📋 해결 방법 보기", expanded=True):
                                st.markdown("""
                                ### Windows에서 긴 경로 지원 활성화 필요
                                
                                **방법 1: Git 설정 (권장)**
                                1. **관리자 권한**으로 PowerShell 실행
                                2. 다음 명령 실행:
                                ```powershell
                                git config --system core.longpaths true
                                ```
                                3. 프로그램 재시작
                                
                                **방법 2: Windows 레지스트리 설정**
                                1. **관리자 권한**으로 레지스트리 편집기 실행 (`regedit`)
                                2. 다음 경로로 이동:
                                   `HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem`
                                3. `LongPathsEnabled` 값을 `1`로 설정 (DWORD)
                                4. 시스템 재시작
                                
                                **방법 3: 로컬 저장소 사용**
                                - 원격 저장소를 먼저 로컬에 clone한 후 로컬 경로 사용
                                """)

                            st.info("💡 설정 후 프로그램을 재시작하고 다시 시도하세요.")
                        else:
                            st.error(f"Indexing failed: {e}")

                        logger.exception("Indexing error")

    with col2:
        delete_index_btn = st.button("🗑️ Delete Index", use_container_width=True)

        if delete_index_btn:
            if st.session_state.get('confirm_delete_index'):
                try:
                    indexer = CommitIndexer(
                        search_client,
                        index_client,
                        llm_client,
                        index_name
                    )
                    indexer.delete_index()
                    st.success("✓ Index deleted")
                    st.session_state.confirm_delete_index = False
                except Exception as e:
                    st.error(f"Delete failed: {e}")
            else:
                st.session_state.confirm_delete_index = True
                st.session_state.confirm_clear_cache = False  # 다른 버튼 상태 리셋
                st.warning("⚠️ Click again to confirm deletion")

    # 캐시 관리
    st.divider()
    st.subheader("💾 Cache Management")

    cache = RepoCloneCache()
    cache_info = cache.get_cache_info()

    col_cache1, col_cache2 = st.columns(2)

    with col_cache1:
        st.metric("Cached Repositories", cache_info['cached_repos'])
        if cache_info['cache_dir']:
            st.caption(f"Cache dir: `{cache_info['cache_dir']}`")

    with col_cache2:
        clear_cache_btn = st.button("🧹 Clear Cache", use_container_width=True)

        if clear_cache_btn:
            if st.session_state.get('confirm_clear_cache'):
                try:
                    cache.clear_all()
                    st.success("✓ Cache cleared")
                    st.session_state.confirm_clear_cache = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to clear cache: {e}")
            else:
                st.session_state.confirm_clear_cache = True
                st.session_state.confirm_delete_index = False  # 다른 버튼 상태 리셋
                st.warning("⚠️ Click again to confirm cache clearing")

# Main content - Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Commit Summary",
    "🔍 Search Commits",
    "👥 Contributors Analysis",
    "🐛 Bug Commits"
])

# Tab 1: Commit Summary
with tab1:
    st.header("최근 커밋 요약")
    st.markdown("LLM을 활용하여 최근 커밋들을 분석하고 요약합니다.")

    col1, col2 = st.columns([3, 1])
    with col1:
        summary_limit = st.slider("분석할 커밋 수", 10, 200, 50)
    with col2:
        generate_summary_btn = st.button("📊 Generate Summary", use_container_width=True)

    if generate_summary_btn:
        with st.spinner("Analyzing repository..."):
            try:
                summary = get_commit_summary(repo_path, llm_client, limit=summary_limit)
                st.markdown("### 📋 분석 결과")
                st.markdown(summary)
            except Exception as e:
                st.error(f"Error: {e}")
                logger.exception("Failed to generate summary")

# Tab 2: Search Commits
with tab2:
    st.header("커밋 검색")
    st.markdown("자연어 쿼리로 커밋을 검색합니다 (벡터 + 하이브리드 검색).")

    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Search Query",
            placeholder="예: 로그인 기능 버그 수정",
            help="검색하고 싶은 내용을 자연어로 입력하세요"
        )
    with col2:
        top_k = st.number_input("Results", 5, 50, 10)

    search_btn = st.button("🔍 Search", use_container_width=True)

    if search_btn and query:
        with st.spinner("Searching..."):
            try:
                results = search_commits(query, search_client, llm_client, top=top_k)

                if results:
                    st.success(f"Found {len(results)} results")

                    for i, result in enumerate(results, 1):
                        with st.expander(f"#{i} [{result['date']}] {result['message'][:80]}...", expanded=(i == 1)):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**Author:** {result['author']}")
                                st.markdown(f"**Message:** {result['message']}")
                                st.markdown(f"**Files:** {result['files']}")

                                # 새로운 메타데이터 표시
                                if result.get('context'):
                                    st.markdown(f"**변경 문맥:** {result['context']}")

                                if result.get('functions'):
                                    st.markdown(f"**수정된 함수:** {result['functions']}")

                                if result.get('classes'):
                                    st.markdown(f"**수정된 클래스:** {result['classes']}")

                                if result.get('impact'):
                                    with st.expander("영향 범위 보기"):
                                        st.text(result['impact'])

                            with col2:
                                st.metric("Score", f"{result['score']:.2f}")
                                st.metric("Changes", result['changes'])
                                st.metric("Complexity", result.get('complexity', 'unknown'))
                                st.info(f"관계: {result.get('relation', 'N/A')}")

                            st.code(result['commit_id'], language=None)
                else:
                    st.warning("No results found")

            except Exception as e:
                st.error(f"Search failed: {e}")
                logger.exception("Search error")

# Tab 3: Contributors Analysis
with tab3:
    st.header("기여자 분석")
    st.markdown("저장소의 기여자들을 분석하고 평가합니다.")

    col1, col2 = st.columns([3, 1])
    with col1:
        contrib_limit = st.slider("분석할 커밋 수", 50, 200, 100, key="contrib_limit")
    with col2:
        analyze_btn = st.button("📊 Analyze", use_container_width=True)

    if analyze_btn:
        with st.spinner("Analyzing contributors..."):
            try:
                result = analyze_contributors(
                    repo_path,
                    criteria=contributor_criteria,
                    limit=contrib_limit
                )

                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    # Overview metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Contributors", result['total_contributors'])
                    col2.metric("Total Commits", result['total_commits'])
                    col3.metric("Avg Commits/Contributor",
                               f"{result['total_commits'] / result['total_contributors']:.1f}")

                    st.markdown("### 📊 기여자별 상세 통계")

                    # Top contributors table
                    for i, contrib in enumerate(result['contributors'][:10], 1):
                        with st.expander(f"#{i} {contrib['name']} - {contrib['commits']} commits",
                                       expanded=(i <= 3)):
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Commits", contrib['commits'])
                            col2.metric("Files Changed", contrib['files_changed'])
                            col3.metric("Lines Added", contrib['lines_added'])
                            col4.metric("Lines Deleted", contrib['lines_deleted'])

                            st.markdown("**Recent Commits:**")
                            for commit in contrib['recent_commits']:
                                st.markdown(f"- `{commit['date']}`: {commit['message']}")

            except Exception as e:
                st.error(f"Analysis failed: {e}")
                logger.exception("Contributor analysis error")

# Tab 4: Bug Commits
with tab4:
    st.header("버그 관련 커밋")
    st.markdown("버그 수정 커밋을 찾아 분석합니다.")

    col1, col2 = st.columns([3, 1])
    with col1:
        bug_limit = st.slider("분석할 커밋 수", 50, 500, 200, key="bug_limit")
    with col2:
        find_bugs_btn = st.button("🐛 Find Bugs", use_container_width=True)

    if find_bugs_btn:
        with st.spinner("Finding bug-related commits..."):
            try:
                bug_commits = find_frequent_bug_commits(repo_path, llm_client, limit=bug_limit)

                if bug_commits:
                    st.success(f"Found {len(bug_commits)} bug-related commits")

                    # Statistics
                    col1, col2 = st.columns(2)
                    col1.metric("Total Bug Commits", len(bug_commits))
                    col2.metric("Bug Rate", f"{len(bug_commits)/bug_limit*100:.1f}%")

                    st.markdown("### 🐛 Bug Fix Commits")

                    for commit in bug_commits[:20]:
                        with st.expander(f"[{commit['date']}] {commit['message'][:80]}..."):
                            st.markdown(f"**Commit ID:** `{commit['id']}`")
                            st.markdown(f"**Author:** {commit['author']}")
                            st.markdown(f"**Date:** {commit['date']}")
                            st.markdown(f"**Files Changed:** {commit['files_changed']}")
                            st.markdown(f"**Message:** {commit['message']}")
                else:
                    st.info("No bug-related commits found")

            except Exception as e:
                st.error(f"Error: {e}")
                logger.exception("Bug commit search error")

# Footer
st.divider()
st.markdown("---")
st.markdown("🚀 **Git History Generator** | Powered by Azure OpenAI & Azure AI Search")
