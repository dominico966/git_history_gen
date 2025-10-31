#!/usr/bin/env python
"""원격 저장소 인덱싱 테스트"""
import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.tools import get_commit_count

print("=" * 80)
print("원격 저장소 접근 테스트")
print("=" * 80)

# 테스트할 저장소들
test_repos = [
    "https://github.com/chromiumembedded/cef",
    "https://github.com/torvalds/linux",
]

for repo_url in test_repos:
    print(f"\n📦 테스트 중: {repo_url}")
    try:
        result = get_commit_count(repo_path=repo_url)
        print(f"✅ 성공: {result}")
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)

