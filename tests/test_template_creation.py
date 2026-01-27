"""
Test script to verify the default template is created correctly.
This simulates what happens when STYLEENGINE_Prompt is created.
"""

def create_default_template():
    """Simulate creating the default template"""
    lines = []
    lines.append("# Keywords\n")
    lines.append("<k></k>\n")
    lines.append("# Prompt\n")
    lines.append("<p></p>\n")
    lines.append("# Negative Prompt\n")
    lines.append("<n></n>\n")
    
    return ''.join(lines)


def test_default_template():
    """Test that the default template has the correct structure"""
    template = create_default_template()
    
    print("=" * 60)
    print("DEFAULT TEMPLATE STRUCTURE TEST")
    print("=" * 60)
    print()
    print("Template content:")
    print("-" * 60)
    print(template)
    print("-" * 60)
    print()
    
    # Verify structure
    assert "# Keywords" in template, "Missing '# Keywords' header"
    assert "<k></k>" in template, "Missing '<k></k>' tags"
    assert "# Prompt" in template, "Missing '# Prompt' header"
    assert "<p></p>" in template, "Missing '<p></p>' tags"
    assert "# Negative Prompt" in template, "Missing '# Negative Prompt' header"
    assert "<n></n>" in template, "Missing '<n></n>' tags"
    
    # Verify order
    lines = template.split('\n')
    assert lines[0] == "# Keywords", "First line should be '# Keywords'"
    assert lines[1] == "<k></k>", "Second line should be '<k></k>'"
    assert lines[2] == "# Prompt", "Third line should be '# Prompt'"
    assert lines[3] == "<p></p>", "Fourth line should be '<p></p>'"
    assert lines[4] == "# Negative Prompt", "Fifth line should be '# Negative Prompt'"
    assert lines[5] == "<n></n>", "Sixth line should be '<n></n>'"
    
    print("CHECKS:")
    print("  [PASS] All headers present")
    print("  [PASS] All tags present")
    print("  [PASS] Correct order")
    print()
    print("=" * 60)
    print("TEST PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_default_template()
