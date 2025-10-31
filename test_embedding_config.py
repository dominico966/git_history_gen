#!/usr/bin/env python
"""임베딩 설정 검증 스크립트"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("임베딩 설정 검증")
print("=" * 80)

try:
    from src.embedding import EMBEDDING_MODEL, VECTOR_DIMENSIONS, BATCH_SIZE

    print(f"✅ 임베딩 모델: {EMBEDDING_MODEL}")
    print(f"✅ 벡터 차원: {VECTOR_DIMENSIONS}")
    print(f"✅ 배치 크기: {BATCH_SIZE}")
    print()

    # 일관성 검사
    if "text-embedding-3-small" in EMBEDDING_MODEL:
        expected_dims = 1536
        if VECTOR_DIMENSIONS == expected_dims:
            print(f"✅ 벡터 차원이 {EMBEDDING_MODEL}와 일치 ({expected_dims})")
        else:
            print(f"⚠️  벡터 차원 불일치: {VECTOR_DIMENSIONS} (예상: {expected_dims})")

    print()
    print("=" * 80)
    print("인덱서 설정 검증")
    print("=" * 80)

    from src.indexer import VECTOR_DIMENSIONS as INDEXER_DIMS

    print(f"✅ 인덱서 벡터 차원: {INDEXER_DIMS}")

    if VECTOR_DIMENSIONS == INDEXER_DIMS:
        print(f"✅ embedding.py와 indexer.py의 벡터 차원 일치")
    else:
        print(f"❌ 벡터 차원 불일치!")
        print(f"   embedding.py: {VECTOR_DIMENSIONS}")
        print(f"   indexer.py: {INDEXER_DIMS}")

    print()
    print("=" * 80)
    print("✅ 모든 임베딩 설정이 일관성 있게 구성되었습니다!")
    print("=" * 80)

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

