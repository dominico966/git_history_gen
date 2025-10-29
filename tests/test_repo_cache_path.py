"""
repo_cache.py의 경로 생성 테스트
"""

import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.repo_cache import RepoCloneCache


def test_cache_path():
    """캐시 경로가 올바르게 생성되는지 테스트"""
    # 싱글톤 리셋 (깨끗한 상태에서 시작)
    RepoCloneCache.reset_instance()

    cache = RepoCloneCache()

    info = cache.get_cache_info()

    print("\n" + "=" * 60)
    print("캐시 경로 정보:")
    print("=" * 60)
    print(f"Cache directory: {info['cache_dir']}")
    print(f"Cache file: {info['cache_file']}")
    print(f"Cached repos: {info['cached_repos']}")
    print("=" * 60)

    # 경로 검증 1: .cache가 경로에 포함되어야 함
    cache_dir = info['cache_dir']
    assert '.cache' in cache_dir, f"Expected '.cache' in path, got: {cache_dir}"

    # 경로 검증 2: git_history_gen\.cache 형식이어야 함 (백슬래시 뒤에 .cache)
    assert 'git_history_gen\\.cache' in cache_dir or 'git_history_gen/.cache' in cache_dir, \
        f"Expected proper path separator after 'git_history_gen', got: {cache_dir}"

    # 경로 검증 3: git_history_gen.cache (점으로 붙어있는 형식)가 아니어야 함
    assert 'git_history_gen.cache' not in cache_dir.replace('\\', '/'), \
        f"Path should NOT contain 'git_history_gen.cache' (dot without separator), got: {cache_dir}"

    print("✓ 경로 검증 성공!")

    # Path 객체로도 확인
    cache_path = Path(cache_dir)
    print(f"\nPath parts: {cache_path.parts}")

    # .cache가 별도의 디렉토리로 존재하는지 확인
    assert cache_path.parent.name == '.cache', \
        f"Expected parent directory to be '.cache', got: {cache_path.parent.name}"

    # 프로젝트 루트 확인
    project_root = cache_path.parent.parent
    assert project_root.name == 'git_history_gen', \
        f"Expected project root to be 'git_history_gen', got: {project_root.name}"

    print("✓ Path 검증 성공!")
    print("\n모든 경로 검증 완료! ✓")


if __name__ == "__main__":
    test_cache_path()

