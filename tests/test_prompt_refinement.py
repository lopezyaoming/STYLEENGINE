#!/usr/bin/env python3
"""
Test script for prompt refinement regex patterns.
Validates extraction and replacement of <p> content.
"""

import re

def test_extract_p_content():
    """Test extracting content from <p> tags"""
    test_cases = [
        # (input, expected_output)
        ('<p>simple prompt</p>', 'simple prompt'),
        ('# Keywords\n<k>8k</k>\n# Prompt\n<p>dragon flying</p>\n# Negative\n<n>ugly</n>', 'dragon flying'),
        ('<P>UPPERCASE TAGS</P>', 'UPPERCASE TAGS'),
        ('<p>multiline\nprompt\ntext</p>', 'multiline\nprompt\ntext'),
        ('<p>  spaces around  </p>', 'spaces around'),
    ]
    
    print("="*60)
    print("TEST: Extract <p> Content")
    print("="*60)
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        p_match = re.search(r'<p>(.*?)</p>', input_text, re.DOTALL | re.IGNORECASE)
        if p_match:
            result = p_match.group(1).strip()
            status = "PASS" if result == expected else "FAIL"
            print(f"\nTest {i}: {status}")
            print(f"  Input: {repr(input_text[:50])}")
            print(f"  Expected: {repr(expected)}")
            print(f"  Got: {repr(result)}")
        else:
            print(f"\nTest {i}: FAIL (no match)")
            print(f"  Input: {repr(input_text[:50])}")

def test_replace_p_content():
    """Test replacing content within <p> tags"""
    test_cases = [
        # (input, replacement, expected_output)
        (
            '<p>old prompt</p>',
            'new refined prompt',
            '<p>new refined prompt</p>'
        ),
        (
            '# Keywords\n<k>8k</k>\n# Prompt\n<p>old</p>\n# Negative\n<n>ugly</n>',
            'refined text here',
            '# Keywords\n<k>8k</k>\n# Prompt\n<p>refined text here</p>\n# Negative\n<n>ugly</n>'
        ),
        (
            '<P>UPPERCASE</P>',
            'refined',
            '<P>refined</P>'
        ),
        (
            '<p>multi\nline\nold</p>',
            'single line new',
            '<p>single line new</p>'
        ),
    ]
    
    print("\n" + "="*60)
    print("TEST: Replace <p> Content")
    print("="*60)
    
    for i, (input_text, replacement, expected) in enumerate(test_cases, 1):
        result = re.sub(
            r'(<p>)(.*?)(</p>)',
            r'\1' + replacement + r'\3',
            input_text,
            flags=re.DOTALL | re.IGNORECASE
        )
        status = "PASS" if result == expected else "FAIL"
        print(f"\nTest {i}: {status}")
        print(f"  Input: {repr(input_text[:50])}")
        print(f"  Replacement: {repr(replacement)}")
        print(f"  Expected: {repr(expected)}")
        print(f"  Got: {repr(result)}")

def test_preserve_other_tags():
    """Test that <k> and <n> tags are not affected"""
    input_text = """# Keywords
<k>fantasy, 8k, concept art</k>
# Prompt
<p>old dragon prompt</p>
# Negative Prompt
<n>blurry, ugly, low quality</n>
"""
    
    replacement = "refined dragon flying over castle"
    
    result = re.sub(
        r'(<p>)(.*?)(</p>)',
        r'\1' + replacement + r'\3',
        input_text,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    print("\n" + "="*60)
    print("TEST: Preserve Other Tags")
    print("="*60)
    
    # Check that <k> and <n> are unchanged
    k_match = re.search(r'<k>(.*?)</k>', result, re.DOTALL | re.IGNORECASE)
    n_match = re.search(r'<n>(.*?)</n>', result, re.DOTALL | re.IGNORECASE)
    p_match = re.search(r'<p>(.*?)</p>', result, re.DOTALL | re.IGNORECASE)
    
    print(f"\n<k> tag preserved: {'PASS' if k_match and 'fantasy' in k_match.group(1) else 'FAIL'}")
    print(f"  Content: {repr(k_match.group(1).strip()) if k_match else 'NOT FOUND'}")
    
    print(f"\n<n> tag preserved: {'PASS' if n_match and 'blurry' in n_match.group(1) else 'FAIL'}")
    print(f"  Content: {repr(n_match.group(1).strip()) if n_match else 'NOT FOUND'}")
    
    print(f"\n<p> tag updated: {'PASS' if p_match and replacement in p_match.group(1) else 'FAIL'}")
    print(f"  Content: {repr(p_match.group(1).strip()) if p_match else 'NOT FOUND'}")

def test_edge_cases():
    """Test edge cases and error conditions"""
    print("\n" + "="*60)
    print("TEST: Edge Cases")
    print("="*60)
    
    # No <p> tag
    text1 = "just plain text"
    match1 = re.search(r'<p>(.*?)</p>', text1, re.DOTALL | re.IGNORECASE)
    print(f"\nNo <p> tag: {'PASS' if not match1 else 'FAIL'}")
    print(f"  Result: {match1 is None}")
    
    # Empty <p> tag
    text2 = "<p></p>"
    match2 = re.search(r'<p>(.*?)</p>', text2, re.DOTALL | re.IGNORECASE)
    print(f"\nEmpty <p> tag: {'PASS' if match2 and not match2.group(1).strip() else 'FAIL'}")
    print(f"  Content: {repr(match2.group(1).strip()) if match2 else 'NO MATCH'}")
    
    # Multiple <p> tags (should match first)
    text3 = "<p>first</p> some text <p>second</p>"
    match3 = re.search(r'<p>(.*?)</p>', text3, re.DOTALL | re.IGNORECASE)
    print(f"\nMultiple <p> tags: {'PASS' if match3 and match3.group(1) == 'first' else 'FAIL'}")
    print(f"  Matched: {repr(match3.group(1)) if match3 else 'NO MATCH'}")

if __name__ == "__main__":
    test_extract_p_content()
    test_replace_p_content()
    test_preserve_other_tags()
    test_edge_cases()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60)
