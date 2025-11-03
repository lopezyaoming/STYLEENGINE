#!/usr/bin/env python3
"""
Audit Python files for hardcoded Windows path separators and other
cross-platform compatibility issues.

Usage:
    python audit_paths.py
"""

import re
from pathlib import Path

def audit_file(filepath):
    """Check a file for hardcoded path separators and compatibility issues."""
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return [(0, f"Error reading file: {e}", "READ_ERROR")]
    
    for i, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        
        # 1. Look for hardcoded Windows absolute paths (e.g., "C:\\")
        if re.search(r'["\'][A-Za-z]:\\\\', line):
            issues.append((i, line.strip()[:80], "Hardcoded Windows absolute path"))
        
        # 2. Look for hardcoded backslashes in paths (not in regexes)
        # Exclude: escape sequences (\n, \t), regex patterns, replace operations
        if '\\\\' in line or '\\\'' in line or '\\"' in line:
            # Check if it's actually a path (has common path patterns)
            if any(pattern in line for pattern in ['temp\\\\', 'data\\\\', 'scripts\\\\', 'addons\\\\']):
                if 'replace' not in line and 'sep' not in line:
                    issues.append((i, line.strip()[:80], "Hardcoded backslash in path"))
        
        # 3. Look for path string concatenation (should use os.path.join or Path)
        # Pattern: variable + "/" + string or variable + "\\" + string
        if re.search(r'\w+\s*\+\s*["\'][/\\]', line) or re.search(r'["\'][/\\]\s*\+\s*\w+', line):
            if 'os.path.join' not in line and 'Path' not in line:
                issues.append((i, line.strip()[:80], "String concatenation for paths (use os.path.join or Path)"))
        
        # 4. Check for replace operations that should be bidirectional
        if '.replace("\\\\", "/")' in line and '.replace("/", "\\\\")' not in stripped:
            # This is actually OK - converting to forward slashes is cross-platform safe
            pass
        
        # 5. Look for hardcoded temp paths
        if re.search(r'["\']/?tmp/|["\']C:\\\\temp', line, re.IGNORECASE):
            issues.append((i, line.strip()[:80], "Hardcoded temp path (use tempfile module)"))
    
    return issues

def main():
    addon_dir = Path(__file__).parent / "styleengine"
    
    print("🔍 Style Engine Path Separator Audit")
    print("=" * 50)
    print()
    
    if not addon_dir.exists():
        print(f"❌ Addon directory not found: {addon_dir}")
        return 1
    
    print(f"📂 Scanning directory: {addon_dir}")
    print()
    
    all_issues = []
    files_scanned = 0
    
    for py_file in sorted(addon_dir.glob("*.py")):
        files_scanned += 1
        issues = audit_file(py_file)
        if issues:
            all_issues.append((py_file.name, issues))
    
    print(f"📄 Scanned {files_scanned} Python files")
    print()
    
    if all_issues:
        print("⚠️ Found potential cross-platform issues:")
        print()
        
        for filename, issues in all_issues:
            print(f"📄 {filename}:")
            for line_num, line_text, issue_type in issues:
                print(f"  Line {line_num}: {issue_type}")
                print(f"    {line_text}")
            print()
        
        print("=" * 50)
        print(f"⚠️ Total: {sum(len(issues) for _, issues in all_issues)} issues in {len(all_issues)} files")
        print()
        print("Recommendations:")
        print("  • Use os.path.join() or pathlib.Path for all path operations")
        print("  • Use .replace('\\\\', '/') when sending paths to external systems")
        print("  • Use tempfile.gettempdir() instead of hardcoded temp paths")
        print("  • Test on macOS/Linux before release")
        return 1
    else:
        print("✅ No cross-platform issues found!")
        print("✅ All path operations appear to be platform-safe")
        return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())

