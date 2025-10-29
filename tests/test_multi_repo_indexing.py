"""
다중 저장소 인덱싱 테스트
서로 다른 git repo를 인덱싱할 때 커밋이 섞이지 않는지 확인
"""
import pytest
from src.indexer import normalize_repo_identifier


def test_normalize_repo_identifier_url():
    """URL 정규화 테스트"""
    # 같은 저장소, 다른 표현
    url1 = "https://github.com/user/repo"
    url2 = "https://github.com/user/repo.git"
    url3 = "https://github.com/user/repo/"

    id1 = normalize_repo_identifier(url1)
    id2 = normalize_repo_identifier(url2)
    id3 = normalize_repo_identifier(url3)

    # 모두 같은 repo_id를 생성해야 함
    assert id1 == id2 == id3, f"같은 저장소가 다른 ID 생성: {id1}, {id2}, {id3}"

    # 다른 저장소는 다른 ID
    different_url = "https://github.com/user/other-repo"
    different_id = normalize_repo_identifier(different_url)
    assert different_id != id1, "다른 저장소가 같은 ID 생성"


def test_normalize_repo_identifier_local():
    """로컬 경로 정규화 테스트"""
    from pathlib import Path
    import tempfile
    import os

    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory() as tmpdir:
        # 같은 경로, 다른 표현
        abs_path = Path(tmpdir).resolve()

        # 현재 디렉토리 변경
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # 절대 경로와 상대 경로 "." 모두 같은 ID 생성해야 함
            id1 = normalize_repo_identifier(str(abs_path))
            id2 = normalize_repo_identifier(".")

            assert id1 == id2, f"같은 경로가 다른 ID 생성: {id1}, {id2}"
        finally:
            os.chdir(old_cwd)


def test_normalize_repo_identifier_different():
    """다른 저장소는 다른 ID를 생성하는지 확인"""
    repos = [
        "https://github.com/user1/repo1",
        "https://github.com/user1/repo2",
        "https://github.com/user2/repo1",
        "https://gitlab.com/user1/repo1",
    ]

    ids = [normalize_repo_identifier(repo) for repo in repos]

    # 모두 다른 ID여야 함
    assert len(ids) == len(set(ids)), f"다른 저장소가 같은 ID 생성: {ids}"


def test_repo_id_format():
    """repo_id 형식 확인"""
    repo_id = normalize_repo_identifier("https://github.com/test/repo")

    # 16자 hex string이어야 함
    assert len(repo_id) == 16, f"repo_id 길이가 16이 아님: {len(repo_id)}"
    assert all(c in '0123456789abcdef' for c in repo_id), f"repo_id가 hex가 아님: {repo_id}"


def test_desired_behavior_documentation():
    """
    원하는 동작 문서화

    시나리오:
    1. repo1을 인덱싱 -> repo_id_1로 저장
    2. repo2를 인덱싱 -> repo_id_2로 저장
    3. repo1의 커밋 검색 -> repo_id_1 필터 적용
    4. 모든 저장소 검색 -> 필터 없음
    """
    repo1 = "https://github.com/user/project1"
    repo2 = "https://github.com/user/project2"

    id1 = normalize_repo_identifier(repo1)
    id2 = normalize_repo_identifier(repo2)

    assert id1 != id2, "다른 저장소는 다른 ID를 가져야 함"

    # 필터 표현식 예시
    filter1 = f"repo_id eq '{id1}'"
    filter2 = f"repo_id eq '{id2}'"

    assert filter1 != filter2
    assert "repo_id eq" in filter1


