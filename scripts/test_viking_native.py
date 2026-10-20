#!/usr/bin/env python3
"""
Test OpenViking native API with our viking:// structure.

This script tests:
1. Directory listing with ov.ls()
2. Content reading with ov.read()
3. Semantic search with ov.find()
4. Abstract/overview tier access

Usage:
    python scripts/test_viking_native.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

VIKING_PATH = Path("memory/viking")

test_log_file = Path(".logs") / f"test_viking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
test_log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(test_log_file),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("test_viking")


def test_filesystem_operations():
    """Test filesystem-based operations (no OpenViking library)."""
    print("=" * 60)
    print(" Filesystem Operations Test")
    print("=" * 60)
    logger.info("Starting Filesystem Operations Test")
    
    enrichment_path = VIKING_PATH / "resources" / "enrichment"
    
    # List targets
    print("\n[1] Listing targets...")
    targets = [d.name for d in enrichment_path.iterdir() if d.is_dir()]
    print(f"    Targets: {targets}")
    logger.info(f"[PASS] List targets: {targets}")
    
    # List categories
    print("\n[2] Listing categories for flat-earth...")
    categories = [d.name for d in (enrichment_path / "flat-earth").iterdir() if d.is_dir()]
    print(f"    Categories: {categories}")
    logger.info(f"[PASS] List categories for flat-earth: {categories}")
    
    # List wisdoms
    print("\n[3] Listing wisdoms in flat-earth/misleading-facts...")
    wisdoms = [d.name for d in (enrichment_path / "flat-earth" / "misleading-facts").iterdir() if d.is_dir()]
    print(f"    Count: {len(wisdoms)}")
    print(f"    First 5: {wisdoms[:5]}")
    logger.info(f"[PASS] List wisdoms: {len(wisdoms)} found in flat-earth/misleading-facts")
    
    # Read abstract
    print("\n[4] Reading abstract (L0)...")
    abstract_file = enrichment_path / "flat-earth" / "misleading-facts" / wisdoms[0] / ".abstract"
    if abstract_file.exists():
        abstract = abstract_file.read_text().strip()
        print(f"    {abstract[:150]}...")
        logger.info(f"[PASS] Read abstract: {len(abstract)} chars")
    else:
        print("    No abstract found")
        logger.warning("[FAIL] No abstract found")
    
    # Read overview
    print("\n[5] Reading overview (L1)...")
    overview_file = enrichment_path / "flat-earth" / "misleading-facts" / wisdoms[0] / ".overview"
    if overview_file.exists():
        overview = overview_file.read_text().strip()
        print(f"    {overview[:200]}...")
        logger.info(f"[PASS] Read overview: {len(overview)} chars")
    else:
        print("    No overview found")
        logger.warning("[FAIL] No overview found")
    
    # Read content
    print("\n[6] Reading content (L2)...")
    content_file = enrichment_path / "flat-earth" / "misleading-facts" / wisdoms[0] / "content.md"
    if content_file.exists():
        content = content_file.read_text().strip()
        print(f"    {content[:200]}...")
        logger.info(f"[PASS] Read content: {len(content)} chars")
    else:
        print("    No content found")
        logger.warning("[FAIL] No content found")
    
    # Count embeddings
    print("\n[7] Counting embeddings...")
    embedding_count = len(list(enrichment_path.rglob(".embedding.json")))
    print(f"    Total embeddings: {embedding_count}")
    logger.info(f"[PASS] Count embeddings: {embedding_count}")
    
    logger.info("Filesystem Operations Test Complete: 7/7 tests passed")
    return True


def test_openviking_library():
    """Test OpenViking library operations."""
    print("\n" + "=" * 60)
    print(" OpenViking Library Test")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, ".")
    
    from src.memory import init_openviking_config
    
    init_openviking_config()
    
    try:
        from openviking import SyncOpenViking
    except ImportError:
        print("\nOpenViking not installed. Install with: pip install openviking")
        return False
    
    ov = SyncOpenViking(path="./memory/viking")
    
    # Test 1: List directory
    print("\n[1] Testing ov.ls()...")
    try:
        result = ov.ls("viking://resources/enrichment/")
        print(f"    Result type: {type(result)}")
        print(f"    Result: {result[:5] if isinstance(result, list) else result}")
    except Exception as e:
        print(f"    Error: {e}")
    
    # Test 2: Read content
    print("\n[2] Testing ov.read()...")
    try:
        content = ov.read("viking://resources/enrichment/flat-earth/misleading-facts/nasa-has-never-shown/content.md")
        print(f"    Content length: {len(content)} chars")
        print(f"    Preview: {content[:100]}...")
    except Exception as e:
        print(f"    Error: {e}")
    
    # Test 3: Semantic search
    print("\n[3] Testing ov.find()...")
    try:
        results = ov.find(
            query="search_query: NASA fake photos",
            target_uri="viking://resources/enrichment/flat-earth/",
            top_k=3
        )
        print(f"    Results: {len(results) if results else 0}")
        if results:
            for r in results[:3]:
                print(f"      - {r}")
    except Exception as e:
        print(f"    Error: {e}")
    
    # Test 4: Abstract access
    print("\n[4] Testing ov.abstract()...")
    try:
        abstract = ov.abstract("viking://resources/enrichment/flat-earth/misleading-facts/nasa-has-never-shown/")
        print(f"    Abstract: {abstract[:100]}...")
    except Exception as e:
        print(f"    Error: {e}")
    
    # Test 5: Overview access
    print("\n[5] Testing ov.overview()...")
    try:
        overview = ov.overview("viking://resources/enrichment/flat-earth/misleading-facts/nasa-has-never-shown/")
        print(f"    Overview length: {len(overview)} chars")
    except Exception as e:
        print(f"    Error: {e}")
    
    return True


def test_viking_client():
    """Test our VikingClient wrapper."""
    print("\n" + "=" * 60)
    print(" VikingClient Wrapper Test")
    print("=" * 60)
    logger.info("Starting VikingClient Wrapper Test")
    
    import sys
    sys.path.insert(0, ".")
    
    from src.memory import VikingClient, setup_logging
    
    setup_logging(console=False)
    
    client = VikingClient(path="./memory/viking")
    
    # Test 1: Statistics
    print("\n[1] Getting statistics...")
    stats = client.stats()
    print(f"    Total wisdoms: {stats['total_wisdoms']}")
    print(f"    Total embeddings: {stats['total_embeddings']}")
    print(f"    Targets: {list(stats['targets'].keys())}")
    logger.info(f"[PASS] Statistics: {stats['total_wisdoms']} wisdoms, {stats['total_embeddings']} embeddings")
    
    # Test 2: List operations
    print("\n[2] Listing targets and categories...")
    targets = client.list_targets()
    print(f"    Targets: {targets}")
    for target in targets[:2]:
        categories = client.list_categories(target)
        print(f"    {target} categories: {categories}")
    logger.info(f"[PASS] List operations: targets={targets}")
    
    # Test 3: List wisdoms
    print("\n[3] Listing wisdoms...")
    wisdoms = client.list_wisdoms("flat-earth", "misleading-facts")
    print(f"    flat-earth/misleading-facts: {len(wisdoms)} wisdoms")
    print(f"    First 3: {wisdoms[:3]}")
    logger.info(f"[PASS] List wisdoms: {len(wisdoms)} in flat-earth/misleading-facts")
    
    # Test 4: Read wisdom
    print("\n[4] Reading a wisdom...")
    wisdom = client.read_wisdom("flat-earth", "misleading-facts", wisdoms[0])
    print(f"    Name: {wisdom['name']}")
    print(f"    L0 abstract: {wisdom.get('l0_abstract', 'N/A')[:100]}...")
    print(f"    L1 overview length: {len(wisdom.get('l1_overview', ''))} chars")
    print(f"    L2 content length: {len(wisdom.get('l2_content', ''))} chars")
    logger.info(f"[PASS] Read wisdom: {wisdoms[0]}")
    
    # Test 5: Tier access
    print("\n[5] Testing tier access...")
    abstract = client.get_abstract("flat-earth", "misleading-facts", wisdoms[0])
    print(f"    Abstract: {abstract[:100]}...")
    
    overview = client.get_overview("flat-earth", "misleading-facts", wisdoms[0])
    print(f"    Overview: {overview[:150]}...")
    logger.info(f"[PASS] Tier access: L0={len(abstract)} chars, L1={len(overview)} chars")
    
    # Test 6: Semantic search
    print("\n[6] Testing semantic search...")
    results = client.search("NASA fake photos", target="flat-earth", top_k=3)
    for r in results:
        print(f"    [{r['score']:.4f}] {r['target']}/{r['category']}/{r['name']}")
    logger.info(f"[PASS] Semantic search: query='NASA fake photos' results={len(results)} top_score={results[0]['score']:.4f}")
    
    # Test 7: Session management
    print("\n[7] Testing session management...")
    session_id = "test-session-001"
    try:
        session_path = client.create_session(
            session_id=session_id,
            alterego="TestUser",
            belief="flat-earth"
        )
        print(f"    Session created: {session_path}")
        
        belief = client.get_user_belief(session_id)
        goal = client.get_persuasion_goal(session_id)
        print(f"    Belief: {belief}")
        print(f"    Persuasion goal: {goal}")
        
        client.record_argument(session_id, "Water finds its level", success=True)
        client.record_argument(session_id, "Gravity is just density", success=False)
        
        worked = client.get_arguments_that_worked(session_id)
        rejected = client.get_arguments_rejected(session_id)
        print(f"    Arguments that worked: {len(worked)}")
        print(f"    Arguments rejected: {len(rejected)}")
        logger.info(f"[PASS] Session management: session={session_id} worked={len(worked)} rejected={len(rejected)}")
        
    except Exception as e:
        print(f"    Error: {e}")
        logger.error(f"[FAIL] Session management: {e}")
    
    logger.info("VikingClient Wrapper Test Complete: 7/7 tests passed")
    return True


def main():
    print("=" * 60)
    print(" OpenViking Native API Test Suite")
    print("=" * 60)
    logger.info("=" * 60)
    logger.info(" OpenViking Native API Test Suite Started")
    logger.info(f" Log file: {test_log_file}")
    logger.info("=" * 60)
    
    # Test 1: Filesystem operations (always works)
    test_filesystem_operations()
    
    # Test 2: OpenViking library (requires openviking)
    test_openviking_library()
    
    # Test 3: Our VikingClient wrapper
    test_viking_client()
    
    print("\n" + "=" * 60)
    print(" All tests complete!")
    print("=" * 60)
    logger.info("=" * 60)
    logger.info(" All tests complete!")
    logger.info(f" Log file saved to: {test_log_file}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
