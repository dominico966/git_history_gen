"""
온라인 Git 저장소에서 파일 내용을 읽고 추가 컨텍스트를 제공하는 도구들
"""

import logging
import requests
from typing import Optional, Dict, List
from urllib.parse import urlparse
import base64
import git
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OnlineRepoReader:
    """온라인 Git 저장소에서 파일 내용을 읽는 클래스"""

    def __init__(self):
        self.github_api_base = "https://api.github.com"
        self.gitlab_api_base = "https://gitlab.com/api/v4"

    def search_github_repo(self, query: str, max_results: int = 5) -> Optional[List[Dict]]:
        """
        GitHub에서 저장소 검색

        Args:
            query: 검색 쿼리 (예: "tauri", "rust webview")
            max_results: 최대 결과 수

        Returns:
            List of repositories with name, full_name, url, description, stars
        """
        try:
            url = f"{self.github_api_base}/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results
            }

            logger.info(f"Searching GitHub for: {query}")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = []

                for item in data.get("items", [])[:max_results]:
                    results.append({
                        "name": item.get("name"),
                        "full_name": item.get("full_name"),
                        "url": item.get("html_url"),
                        "clone_url": item.get("clone_url"),
                        "description": item.get("description", ""),
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language", ""),
                        "topics": item.get("topics", [])
                    })

                logger.info(f"✓ Found {len(results)} repositories")
                return results
            else:
                logger.error(f"GitHub search error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Failed to search GitHub: {e}")
            return None

    def parse_github_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        GitHub URL을 파싱하여 owner, repo, path 추출

        예: https://github.com/owner/repo/blob/main/path/to/file.py
        → {"owner": "owner", "repo": "repo", "ref": "main", "path": "path/to/file.py"}
        """
        try:
            parsed = urlparse(url)
            if "github.com" not in parsed.netloc:
                return None

            parts = parsed.path.strip("/").split("/")
            if len(parts) < 2:
                return None

            owner = parts[0]
            repo = parts[1]

            # blob/main/path/to/file 형식
            if len(parts) >= 4 and parts[2] in ["blob", "tree"]:
                ref = parts[3]
                path = "/".join(parts[4:]) if len(parts) > 4 else ""
            else:
                ref = "main"
                path = ""

            return {
                "owner": owner,
                "repo": repo,
                "ref": ref,
                "path": path
            }
        except Exception as e:
            logger.error(f"Failed to parse GitHub URL: {e}")
            return None

    def get_github_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[str]:
        """
        GitHub API를 사용하여 파일 내용 가져오기

        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            path: 파일 경로
            ref: 브랜치/태그/커밋 (기본: main)

        Returns:
            파일 내용 (텍스트)
        """
        try:
            url = f"{self.github_api_base}/repos/{owner}/{repo}/contents/{path}"
            params = {"ref": ref}

            logger.info(f"Fetching GitHub file: {owner}/{repo}/{path}@{ref}")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # base64로 인코딩된 content 디코딩
                if "content" in data:
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    logger.info(f"✓ Successfully fetched file ({len(content)} chars)")
                    return content
                else:
                    logger.warning(f"No content field in response")
                    return None
            else:
                logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch GitHub file: {e}")
            return None

    def get_github_commit_diff(self, owner: str, repo: str, commit_sha: str) -> Optional[Dict]:
        """
        GitHub API를 사용하여 커밋의 diff 정보 가져오기

        Returns:
            Dict with files, stats, patch info
        """
        try:
            url = f"{self.github_api_base}/repos/{owner}/{repo}/commits/{commit_sha}"

            logger.info(f"Fetching GitHub commit: {owner}/{repo}@{commit_sha[:8]}")
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    "sha": data.get("sha"),
                    "message": data.get("commit", {}).get("message"),
                    "author": data.get("commit", {}).get("author"),
                    "files": data.get("files", []),
                    "stats": data.get("stats")
                }
            else:
                logger.error(f"GitHub API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch GitHub commit: {e}")
            return None

    def get_file_from_url(self, url: str) -> Optional[str]:
        """
        URL에서 파일 내용 가져오기 (GitHub, GitLab 등 자동 감지)
        """
        # GitHub URL 파싱 시도
        github_info = self.parse_github_url(url)
        if github_info:
            return self.get_github_file_content(
                github_info["owner"],
                github_info["repo"],
                github_info["path"],
                github_info["ref"]
            )

        # 직접 HTTP 요청 (raw URL 등)
        try:
            logger.info(f"Trying direct HTTP GET: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"HTTP error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Failed to fetch file from URL: {e}")
            return None


def read_file_from_commit(repo_path: str, commit_sha: str, file_path: str) -> Optional[str]:
    """
    로컬 또는 캐시된 저장소에서 특정 커밋의 파일 내용 읽기

    Args:
        repo_path: 저장소 경로
        commit_sha: 커밋 해시
        file_path: 파일 경로

    Returns:
        파일 내용 (텍스트)
    """
    try:
        from src.repo_cache import RepoCloneCache

        # 원격 저장소면 캐시에서 가져오기
        if repo_path.startswith(('http://', 'https://', 'git@')):
            cache = RepoCloneCache()
            cached_path = cache.get_or_clone(repo_path)
            repo = git.Repo(cached_path)
        else:
            repo = git.Repo(repo_path)

        # 커밋 객체 가져오기
        commit = repo.commit(commit_sha)

        # 파일 내용 읽기
        try:
            blob = commit.tree / file_path
            content = blob.data_stream.read().decode("utf-8")
            logger.info(f"✓ Read file from commit: {file_path}@{commit_sha[:8]} ({len(content)} chars)")
            return content
        except KeyError:
            logger.warning(f"File not found in commit: {file_path}")
            return None

    except Exception as e:
        logger.error(f"Failed to read file from commit: {e}")
        return None


def get_file_context(repo_path: str, commit_sha: str, file_path: str, lines_around: int = 10) -> Optional[Dict]:
    """
    커밋에서 변경된 파일의 주변 컨텍스트 가져오기

    Args:
        repo_path: 저장소 경로
        commit_sha: 커밋 해시
        file_path: 파일 경로
        lines_around: 변경 부분 주변 라인 수

    Returns:
        Dict with file content, changes, context
    """
    try:
        from src.repo_cache import RepoCloneCache

        # 저장소 가져오기
        if repo_path.startswith(('http://', 'https://', 'git@')):
            cache = RepoCloneCache()
            cached_path = cache.get_or_clone(repo_path)
            repo = git.Repo(cached_path)
        else:
            repo = git.Repo(repo_path)

        commit = repo.commit(commit_sha)

        # 파일 전체 내용
        try:
            blob = commit.tree / file_path
            full_content = blob.data_stream.read().decode("utf-8")
        except:
            full_content = None

        # diff 정보 (부모 커밋과 비교)
        if commit.parents:
            parent = commit.parents[0]
            diffs = parent.diff(commit, create_patch=True)

            for diff in diffs:
                if diff.b_path == file_path:
                    return {
                        "file_path": file_path,
                        "commit_sha": commit_sha,
                        "full_content": full_content,
                        "diff": diff.diff.decode("utf-8") if diff.diff else None,
                        "change_type": diff.change_type,
                        "lines_added": diff.diff.decode("utf-8").count("\n+") if diff.diff else 0,
                        "lines_deleted": diff.diff.decode("utf-8").count("\n-") if diff.diff else 0
                    }

        return {
            "file_path": file_path,
            "commit_sha": commit_sha,
            "full_content": full_content,
            "diff": None
        }

    except Exception as e:
        logger.error(f"Failed to get file context: {e}")
        return None



def get_commit_diff(repo_path: str, commit_sha: str, max_files: int = 10) -> Optional[Dict]:
    """
    특정 커밋의 전체 변경사항(diff)을 가져옵니다.

    Args:
        repo_path: 저장소 경로 또는 URL
        commit_sha: 커밋 해시
        max_files: 표시할 최대 파일 수

    Returns:
        Dict with commit info and diffs
    """
    try:
        from src.repo_cache import RepoCloneCache

        # 저장소 가져오기
        if repo_path.startswith(('http://', 'https://', 'git@')):
            cache = RepoCloneCache()
            cached_path = cache.get_or_clone(repo_path)
            repo = git.Repo(cached_path)
        else:
            repo = git.Repo(repo_path)

        commit = repo.commit(commit_sha)

        result = {
            "commit_sha": commit.hexsha,
            "short_sha": commit.hexsha[:8],
            "author": commit.author.name,
            "email": commit.author.email,
            "date": commit.committed_datetime.isoformat(),
            "message": commit.message.strip(),
            "files_changed": [],
            "stats": {
                "files": 0,
                "insertions": 0,
                "deletions": 0
            }
        }

        # diff 정보 (부모 커밋과 비교)
        if commit.parents:
            parent = commit.parents[0]
            diffs = parent.diff(commit, create_patch=True)

            for idx, diff in enumerate(diffs):
                if idx >= max_files:
                    result["files_changed"].append({
                        "note": f"... and {len(diffs) - max_files} more files"
                    })
                    break

                file_info = {
                    "file_path": diff.b_path or diff.a_path,
                    "change_type": diff.change_type,
                    "diff": None
                }

                # diff 텍스트 추출
                if diff.diff:
                    try:
                        diff_text = diff.diff.decode("utf-8")
                        # diff가 너무 길면 앞부분만
                        if len(diff_text) > 2000:
                            file_info["diff"] = diff_text[:2000] + "\n... (diff too long, truncated)"
                        else:
                            file_info["diff"] = diff_text

                        # 통계 계산
                        insertions = diff_text.count("\n+") - diff_text.count("\n+++")
                        deletions = diff_text.count("\n-") - diff_text.count("\n---")
                        file_info["insertions"] = insertions
                        file_info["deletions"] = deletions

                        result["stats"]["insertions"] += insertions
                        result["stats"]["deletions"] += deletions
                    except:
                        file_info["diff"] = "(binary file or decode error)"

                result["files_changed"].append(file_info)
                result["stats"]["files"] += 1

        else:
            # 첫 커밋인 경우
            result["note"] = "Initial commit (no parent to compare)"

        logger.info(f"✓ Got diff for commit {commit_sha[:8]}: {result['stats']['files']} files")
        return result

    except Exception as e:
        logger.error(f"Failed to get commit diff: {e}")
        return None


def get_readme_content(repo_path: str) -> Optional[str]:
    """
    저장소의 README 파일 내용 가져오기

    Args:
        repo_path: 저장소 경로 또는 URL

    Returns:
        README 내용
    """
    try:
        from src.repo_cache import RepoCloneCache

        # 저장소 가져오기
        if repo_path.startswith(('http://', 'https://', 'git@')):
            cache = RepoCloneCache()
            cached_path = cache.get_or_clone(repo_path)
            repo = git.Repo(cached_path)
        else:
            repo = git.Repo(repo_path)

        # README 파일 찾기
        readme_names = ["README.md", "README.MD", "readme.md", "README", "README.txt"]

        for readme_name in readme_names:
            try:
                blob = repo.head.commit.tree / readme_name
                content = blob.data_stream.read().decode("utf-8")
                logger.info(f"✓ Found README: {readme_name} ({len(content)} chars)")
                return content
            except KeyError:
                continue

        logger.warning("No README file found")
        return None

    except Exception as e:
        logger.error(f"Failed to get README: {e}")
        return None

