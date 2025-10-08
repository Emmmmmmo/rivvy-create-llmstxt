#!/usr/bin/env python3
"""
Unit Tests for Breadcrumb Extraction

Tests the breadcrumb extraction functionality to ensure proper categorization
from HTML breadcrumb trails.

Usage:
    python3 tests/test_breadcrumb_extraction.py
"""

import sys
import os
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from update_llms_agnostic import AgnosticLLMsUpdater

# Test HTML samples
TEST_HTML_MYDIY = """
<!DOCTYPE html>
<html>
<head><title>Test Product</title></head>
<body>
<div class="breadcrumb">
<a href="https://www.mydiy.ie/">Home</a>
<a href="https://www.mydiy.ie/power-tools/">Power Tools</a>
<a href="https://www.mydiy.ie/power-tools/angle-grinders-wall-chasers-and-metalworking-tools/">Angle Grinders, Wall Chasers &amp; Metalworking Tools</a>
<a href="https://www.mydiy.ie/power-tools/angle-grinders-wall-chasers-and-metalworking-tools/angle-grinders---100mm-disc/">Angle Grinders - 100mm Disc</a>
</div>
<div class="content">Product content here</div>
</body>
</html>
"""

TEST_HTML_NO_BREADCRUMB = """
<!DOCTYPE html>
<html>
<head><title>Test Product</title></head>
<body>
<div class="content">Product content with no breadcrumb</div>
</body>
</html>
"""

TEST_HTML_HOME_ONLY = """
<!DOCTYPE html>
<html>
<head><title>Test Product</title></head>
<body>
<div class="breadcrumb">
<a href="https://www.mydiy.ie/">Home</a>
</div>
<div class="content">Uncategorized product</div>
</body>
</html>
"""

TEST_HTML_TWO_LEVELS = """
<!DOCTYPE html>
<html>
<head><title>Test Product</title></head>
<body>
<div class="breadcrumb">
<a href="https://www.mydiy.ie/">Home</a>
<a href="https://www.mydiy.ie/hand-tools/">Hand Tools</a>
</div>
<div class="content">Hand tool product</div>
</body>
</html>
"""

TEST_HTML_SPECIAL_CHARS = """
<!DOCTYPE html>
<html>
<head><title>Test Product</title></head>
<body>
<div class="breadcrumb">
<a href="https://www.mydiy.ie/">Home</a>
<a href="https://www.mydiy.ie/workwear/">Workwear, Tool Storage &amp; Safety</a>
<a href="https://www.mydiy.ie/workwear/safety/">Safety Equipment (Professional)</a>
</div>
<div class="content">Safety product</div>
</body>
</html>
"""

def test_extraction_mydiy():
    """Test breadcrumb extraction from MyDIY.ie HTML."""
    print("Test 1: MyDIY.ie multi-level breadcrumb extraction")
    print("-" * 80)
    
    # Create updater instance with proper parameters
    updater = AgnosticLLMsUpdater(
        firecrawl_api_key="test_key",
        domain="mydiy.ie"
    )
    
    breadcrumbs = updater._extract_breadcrumbs_from_html(TEST_HTML_MYDIY)
    
    print(f"Extracted breadcrumbs: {len(breadcrumbs)}")
    for i, bc in enumerate(breadcrumbs):
        print(f"  {i+1}. {bc['text']} -> {bc['url']}")
    
    # Verify extraction
    assert len(breadcrumbs) == 4, f"Expected 4 breadcrumbs, got {len(breadcrumbs)}"
    assert breadcrumbs[0]['text'] == "Home"
    assert breadcrumbs[1]['text'] == "Power Tools"
    assert breadcrumbs[2]['text'] == "Angle Grinders, Wall Chasers & Metalworking Tools"
    assert breadcrumbs[3]['text'] == "Angle Grinders - 100mm Disc"
    
    # Test HTML entity decoding
    assert "&amp;" not in breadcrumbs[2]['text'], "HTML entities not decoded"
    assert "&" in breadcrumbs[2]['text'], "Ampersand should be decoded"
    
    print("✓ PASSED")
    print()
    return True

def test_shard_determination():
    """Test shard name determination from breadcrumbs."""
    print("Test 2: Shard determination from breadcrumbs")
    print("-" * 80)
    
    updater = AgnosticLLMsUpdater(
        firecrawl_api_key="test_key",
        domain="mydiy.ie"
    )
    
    # Test multi-level breadcrumb (should use most specific)
    breadcrumbs = updater._extract_breadcrumbs_from_html(TEST_HTML_MYDIY)
    shard = updater._determine_shard_from_breadcrumbs(breadcrumbs)
    
    print(f"Breadcrumb trail: {' > '.join([bc['text'] for bc in breadcrumbs])}")
    print(f"Determined shard: {shard}")
    
    assert shard == "angle_grinders_100mm_disc", f"Expected 'angle_grinders_100mm_disc', got '{shard}'"
    print("✓ PASSED - Multi-level breadcrumb")
    print()
    
    # Test two-level breadcrumb (should use main category)
    breadcrumbs2 = updater._extract_breadcrumbs_from_html(TEST_HTML_TWO_LEVELS)
    shard2 = updater._determine_shard_from_breadcrumbs(breadcrumbs2)
    
    print(f"Breadcrumb trail: {' > '.join([bc['text'] for bc in breadcrumbs2])}")
    print(f"Determined shard: {shard2}")
    
    assert shard2 == "hand_tools", f"Expected 'hand_tools', got '{shard2}'"
    print("✓ PASSED - Two-level breadcrumb")
    print()
    
    return True

def test_no_breadcrumb():
    """Test handling of missing breadcrumbs."""
    print("Test 3: No breadcrumb handling")
    print("-" * 80)
    
    updater = AgnosticLLMsUpdater(
        firecrawl_api_key="test_key",
        domain="mydiy.ie"
    )
    
    breadcrumbs = updater._extract_breadcrumbs_from_html(TEST_HTML_NO_BREADCRUMB)
    
    print(f"Extracted breadcrumbs: {len(breadcrumbs)}")
    
    assert len(breadcrumbs) == 0, "Should extract no breadcrumbs"
    
    shard = updater._determine_shard_from_breadcrumbs(breadcrumbs)
    print(f"Shard for no breadcrumbs: {shard}")
    
    assert shard == "other_products", f"Expected 'other_products', got '{shard}'"
    print("✓ PASSED")
    print()
    
    return True

def test_home_only():
    """Test handling of Home-only breadcrumb."""
    print("Test 4: Home-only breadcrumb")
    print("-" * 80)
    
    updater = AgnosticLLMsUpdater(
        firecrawl_api_key="test_key",
        domain="mydiy.ie"
    )
    
    breadcrumbs = updater._extract_breadcrumbs_from_html(TEST_HTML_HOME_ONLY)
    
    print(f"Extracted breadcrumbs: {len(breadcrumbs)}")
    for bc in breadcrumbs:
        print(f"  - {bc['text']}")
    
    shard = updater._determine_shard_from_breadcrumbs(breadcrumbs)
    print(f"Shard for Home-only: {shard}")
    
    assert shard == "other_products", f"Expected 'other_products', got '{shard}'"
    print("✓ PASSED")
    print()
    
    return True

def test_special_characters():
    """Test handling of special characters in breadcrumbs."""
    print("Test 5: Special character handling")
    print("-" * 80)
    
    updater = AgnosticLLMsUpdater(
        firecrawl_api_key="test_key",
        domain="mydiy.ie"
    )
    
    breadcrumbs = updater._extract_breadcrumbs_from_html(TEST_HTML_SPECIAL_CHARS)
    
    print(f"Breadcrumb trail: {' > '.join([bc['text'] for bc in breadcrumbs])}")
    
    shard = updater._determine_shard_from_breadcrumbs(breadcrumbs)
    print(f"Determined shard: {shard}")
    
    # Check that special characters are properly cleaned
    assert "(" not in shard, "Parentheses not removed"
    assert ")" not in shard, "Parentheses not removed"
    assert "," not in shard, "Commas not removed"
    assert "&" not in shard, "Ampersand not converted"
    assert "and" in shard or "_" in shard, "Should have converted & to 'and' or removed it"
    
    print(f"✓ PASSED - Special characters cleaned")
    print()
    
    return True

def test_jg_engineering_compatibility():
    """Test that JG Engineering workflow is not affected."""
    print("Test 6: JG Engineering compatibility (should not use breadcrumbs)")
    print("-" * 80)
    
    updater = AgnosticLLMsUpdater(
        firecrawl_api_key="test_key",
        domain="jgengineering.ie"
    )
    
    # JG Engineering config should not have breadcrumbs enabled
    use_breadcrumbs = updater.site_config.get('shard_extraction', {}).get('use_breadcrumbs', False)
    
    print(f"Breadcrumbs enabled: {use_breadcrumbs}")
    assert not use_breadcrumbs, "Breadcrumbs should be disabled for JG Engineering"
    
    print("✓ PASSED - JG Engineering won't use breadcrumbs")
    print()
    
    return True

def run_all_tests():
    """Run all tests."""
    print("=" * 80)
    print("BREADCRUMB EXTRACTION TESTS")
    print("=" * 80)
    print()
    
    tests = [
        test_extraction_mydiy,
        test_shard_determination,
        test_no_breadcrumb,
        test_home_only,
        test_special_characters,
        test_jg_engineering_compatibility
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            print()
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            print()
            failed += 1
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

