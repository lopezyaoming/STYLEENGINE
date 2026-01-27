"""
Test script for the new HTML-style tag prompt parsing system.
Run this to verify the parsing logic works correctly.
"""

import re

def parse_prompt_tags(text):
    """
    Parse HTML-style tags from text.
    
    Expected format:
        <k>keywords here</k>
        <p>main prompt here</p>
        <n>negative prompt here</n>
    """
    parsed = {
        'keywords': '',
        'prompt': '',
        'negative': ''
    }
    
    # Extract keywords (<k>...</k>)
    k_match = re.search(r'<k>(.*?)</k>', text, re.DOTALL | re.IGNORECASE)
    if k_match:
        parsed['keywords'] = ' '.join(k_match.group(1).strip().split())
    
    # Extract prompt (<p>...</p>)
    p_match = re.search(r'<p>(.*?)</p>', text, re.DOTALL | re.IGNORECASE)
    if p_match:
        parsed['prompt'] = ' '.join(p_match.group(1).strip().split())
    
    # Extract negative (<n>...</n>)
    n_match = re.search(r'<n>(.*?)</n>', text, re.DOTALL | re.IGNORECASE)
    if n_match:
        parsed['negative'] = ' '.join(n_match.group(1).strip().split())
    
    return parsed


def build_prompt_from_template(parsed_tags):
    """
    Build final prompt from parsed tags.
    
    Logic: Keywords + Prompt = Final Positive Prompt
    """
    keywords = parsed_tags.get('keywords', '').strip()
    prompt = parsed_tags.get('prompt', '').strip()
    negative = parsed_tags.get('negative', '').strip()
    
    # Concatenate keywords + prompt
    parts = []
    if keywords:
        parts.append(keywords)
    if prompt:
        parts.append(prompt)
    
    final_prompt = ', '.join(parts) if parts else ''
    
    return (final_prompt, negative)


def process_prompt_builder(text):
    """
    Main entry point for prompt builder.
    """
    if not text or not text.strip():
        return ("", "")
    
    # Check if text contains HTML-style tags
    text_lower = text.lower()
    has_tags = ('<k>' in text_lower or '<p>' in text_lower or '<n>' in text_lower)
    
    if not has_tags:
        return (text.strip(), "")
    
    # Parse tags
    parsed = parse_prompt_tags(text)
    
    # Check if we parsed anything meaningful
    if not parsed['keywords'] and not parsed['prompt']:
        return (text.strip(), "")
    
    # Build prompt
    positive, negative = build_prompt_from_template(parsed)
    
    return (positive, negative)


# ================================================================
# TEST CASES
# ================================================================

def test_full_format():
    """Test with all three tags"""
    text = """
    <k>concept art, matte painting, 8k</k>
    <p>futuristic city at night</p>
    <n>blurry, low quality</n>
    """
    
    positive, negative = process_prompt_builder(text)
    
    print("Test 1: Full format")
    print(f"  Positive: '{positive}'")
    print(f"  Negative: '{negative}'")
    
    assert "concept art" in positive
    assert "futuristic city" in positive
    assert positive.startswith("concept art")  # Keywords first
    assert negative == "blurry, low quality"
    print("  PASS\n")


def test_prompt_only():
    """Test with only prompt tag"""
    text = """
    <p>a majestic dragon</p>
    """
    
    positive, negative = process_prompt_builder(text)
    
    print("Test 2: Prompt only")
    print(f"  Positive: '{positive}'")
    print(f"  Negative: '{negative}'")
    
    assert positive == "a majestic dragon"
    assert negative == ""
    print("  PASS\n")


def test_keywords_and_prompt():
    """Test with keywords and prompt only"""
    text = """
    <k>photorealistic, highly detailed</k>
    <p>a modern office building</p>
    """
    
    positive, negative = process_prompt_builder(text)
    
    print("Test 3: Keywords + Prompt")
    print(f"  Positive: '{positive}'")
    print(f"  Negative: '{negative}'")
    
    assert positive == "photorealistic, highly detailed, a modern office building"
    assert negative == ""
    print("  PASS\n")


def test_no_tags():
    """Test fallback with no tags (raw text)"""
    text = "just some raw text without tags"
    
    positive, negative = process_prompt_builder(text)
    
    print("Test 4: No tags (fallback)")
    print(f"  Positive: '{positive}'")
    print(f"  Negative: '{negative}'")
    
    assert positive == text
    assert negative == ""
    print("  PASS\n")


def test_case_insensitive():
    """Test that tags are case-insensitive"""
    text = """
    <K>cinematic</K>
    <P>a sunset scene</P>
    <N>blurry</N>
    """
    
    positive, negative = process_prompt_builder(text)
    
    print("Test 5: Case insensitive tags")
    print(f"  Positive: '{positive}'")
    print(f"  Negative: '{negative}'")
    
    assert "cinematic" in positive
    assert "sunset" in positive
    assert negative == "blurry"
    print("  PASS\n")


def test_multiline_content():
    """Test with multiline content inside tags"""
    text = """
    <k>
    concept art,
    matte painting,
    8k resolution
    </k>
    
    <p>
    a futuristic city
    with flying cars
    and neon lights
    </p>
    
    <n>
    blurry,
    low quality,
    watermark
    </n>
    """
    
    positive, negative = process_prompt_builder(text)
    
    print("Test 6: Multiline content")
    print(f"  Positive: '{positive}'")
    print(f"  Negative: '{negative}'")
    
    # Should normalize spaces
    assert "concept art, matte painting, 8k resolution" in positive
    assert "futuristic city with flying cars and neon lights" in positive
    assert "blurry, low quality, watermark" == negative
    print("  PASS\n")


def test_empty_tags():
    """Test with empty tags"""
    text = """
    <k></k>
    <p>just a prompt</p>
    <n></n>
    """
    
    positive, negative = process_prompt_builder(text)
    
    print("Test 7: Empty tags")
    print(f"  Positive: '{positive}'")
    print(f"  Negative: '{negative}'")
    
    assert positive == "just a prompt"
    assert negative == ""
    print("  PASS\n")


if __name__ == "__main__":
    print("=" * 60)
    print("STYLE ENGINE - PROMPT PARSING TESTS")
    print("=" * 60)
    print()
    
    test_full_format()
    test_prompt_only()
    test_keywords_and_prompt()
    test_no_tags()
    test_case_insensitive()
    test_multiline_content()
    test_empty_tags()
    
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
