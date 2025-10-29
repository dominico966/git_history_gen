"""
원격 저장소 clone 기능 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from src.document_generator import DocumentGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_remote_clone():
    """원격 저장소 clone 테스트"""
    logger.info("=" * 60)
    logger.info("원격 저장소 Clone 테스트")
    logger.info("=" * 60)
    
    # 작은 테스트 저장소 사용
    test_url = "https://github.com/octocat/Hello-World"
    
    try:
        logger.info(f"테스트 URL: {test_url}")
        doc_gen = DocumentGenerator(test_url)
        
        logger.info("✓ Clone 성공")
        
        # 커밋 추출 테스트
        commits = doc_gen.get_commits(limit=5)
        logger.info(f"✓ {len(commits)}개 커밋 추출 성공")
        
        for i, commit in enumerate(commits, 1):
            logger.info(f"  {i}. [{commit['id'][:8]}] {commit['message'][:50]}")
        
        logger.info("\n✓ 원격 저장소 기능 테스트 완료!")
        return True
        
    except Exception as e:
        logger.error(f"✗ 테스트 실패: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_remote_clone()

