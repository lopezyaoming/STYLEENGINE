#!/usr/bin/env python3
"""
Validate Blender addon package structure for cross-platform compatibility.
Exhaustive validation with detailed reporting for developers.

Usage:
    python validate_package.py styleengine.zip
    python validate_package.py styleengine.zip --verbose
"""

import sys
import os
import re
import zipfile
import ast
from pathlib import Path
from collections import defaultdict

class ValidationReport:
    """Structured validation report with categorized issues."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.stats = defaultdict(int)
        
    def add_error(self, message, category="general"):
        self.errors.append({"msg": message, "category": category})
        
    def add_warning(self, message, category="general"):
        self.warnings.append({"msg": message, "category": category})
        
    def add_info(self, message):
        self.info.append(message)
        
    def print_section(self, title):
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")

def check_macos_compatibility(files, zf, report):
    """Exhaustive macOS compatibility checks."""
    print("🍎 Checking macOS Compatibility...")
    
    # 1. Check for macOS hidden files that shouldn't be in the ZIP
    macos_junk = ['.DS_Store', '._.DS_Store', '__MACOSX', '.Spotlight-V100', 
                  '.Trashes', '.fseventsd', '.VolumeIcon.icns', '.AppleDouble']
    
    found_junk = []
    for filename in files:
        for junk in macos_junk:
            if junk in filename:
                found_junk.append(filename)
                report.add_warning(f"macOS hidden file found: {filename}", "macos")
    
    if not found_junk:
        print("  ✅ No macOS hidden files (.DS_Store, __MACOSX, etc.)")
        report.add_info("No macOS hidden files found")
    else:
        print(f"  ⚠️  Found {len(found_junk)} macOS hidden files")
    
    # 2. Check for resource forks (files starting with ._)
    resource_forks = [f for f in files if '/._' in f or f.startswith('._')]
    if resource_forks:
        print(f"  ⚠️  Found {len(resource_forks)} macOS resource fork files")
        report.add_warning(f"Found {len(resource_forks)} resource fork files (._*)", "macos")
        for fork in resource_forks[:3]:
            report.add_warning(f"    {fork}", "macos")
    else:
        print("  ✅ No resource fork files (._*)")
        report.add_info("No resource fork files")
    
    # 3. Check for case-sensitivity issues
    lowercase_map = {}
    case_conflicts = []
    for filename in files:
        lower = filename.lower()
        if lower in lowercase_map:
            case_conflicts.append((lowercase_map[lower], filename))
            report.add_error(
                f"Case conflict: '{lowercase_map[lower]}' vs '{filename}' "
                "(will conflict on case-insensitive macOS filesystems)",
                "macos"
            )
        lowercase_map[lower] = filename
    
    if case_conflicts:
        print(f"  ❌ Found {len(case_conflicts)} case-sensitivity conflicts")
    else:
        print("  ✅ No case-sensitivity conflicts")
        report.add_info("No case-sensitivity conflicts")
    
    # 4. Check for special characters that cause issues on macOS
    problematic_chars = [':', '*', '?', '"', '<', '>', '|']
    files_with_special = []
    for filename in files:
        for char in problematic_chars:
            if char in filename:
                files_with_special.append((filename, char))
                report.add_error(
                    f"Problematic character '{char}' in: {filename}",
                    "macos"
                )
    
    if files_with_special:
        print(f"  ❌ Found {len(files_with_special)} files with problematic characters")
    else:
        print("  ✅ No problematic special characters in filenames")
        report.add_info("No problematic special characters")
    
    # 5. Check for symlinks (stored differently on macOS)
    symlinks = []
    for filename in files:
        info = zf.getinfo(filename)
        # Check if external_attr indicates a symlink (Unix mode)
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            symlinks.append(filename)
            report.add_warning(f"Symlink detected: {filename}", "macos")
    
    if symlinks:
        print(f"  ⚠️  Found {len(symlinks)} symlinks (may not work cross-platform)")
    else:
        print("  ✅ No symlinks detected")
        report.add_info("No symlinks")
    
    report.stats['macos_checks'] = 5

def check_windows_compatibility(files, zf, report):
    """Exhaustive Windows compatibility checks."""
    print("\n🪟 Checking Windows Compatibility...")
    
    # 1. Check for backslashes in paths (critical error)
    backslash_files = [f for f in files if '\\' in f]
    if backslash_files:
        print(f"  ❌ Found {len(backslash_files)} files with backslashes")
        for f in backslash_files:
            report.add_error(f"Windows backslash in path: {f}", "windows")
    else:
        print("  ✅ No Windows backslashes in paths")
        report.add_info("Paths use forward slashes (correct)")
    
    # 2. Check for reserved Windows filenames
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                     'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                     'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    
    reserved_found = []
    for filename in files:
        basename = os.path.basename(filename).split('.')[0].upper()
        if basename in reserved_names:
            reserved_found.append(filename)
            report.add_error(f"Reserved Windows filename: {filename}", "windows")
    
    if reserved_found:
        print(f"  ❌ Found {len(reserved_found)} reserved Windows filenames")
    else:
        print("  ✅ No reserved Windows filenames (CON, PRN, AUX, etc.)")
        report.add_info("No reserved Windows filenames")
    
    # 3. Check for trailing spaces/dots (problematic on Windows)
    trailing_issues = []
    for filename in files:
        parts = filename.split('/')
        for part in parts:
            if part and (part.endswith(' ') or part.endswith('.')):
                trailing_issues.append(filename)
                report.add_error(
                    f"Filename ends with space/dot: {filename} (problematic on Windows)",
                    "windows"
                )
                break
    
    if trailing_issues:
        print(f"  ❌ Found {len(trailing_issues)} files with trailing spaces/dots")
    else:
        print("  ✅ No trailing spaces or dots in filenames")
        report.add_info("No trailing spaces/dots in filenames")
    
    # 4. Check path length (Windows has 260 char limit without long path support)
    long_paths = []
    for filename in files:
        if len(filename) > 200:  # Conservative limit
            long_paths.append((filename, len(filename)))
            report.add_warning(
                f"Long path ({len(filename)} chars): {filename[:50]}...",
                "windows"
            )
    
    if long_paths:
        print(f"  ⚠️  Found {len(long_paths)} potentially long paths")
    else:
        print("  ✅ All paths under 200 characters")
        report.add_info("Path lengths are reasonable")
    
    report.stats['windows_checks'] = 4

def check_linux_compatibility(files, zf, report):
    """Linux-specific compatibility checks."""
    print("\n🐧 Checking Linux Compatibility...")
    
    # 1. Check for executable permissions (shouldn't be needed for Python files)
    executable_files = []
    for filename in files:
        if filename.endswith('.py'):
            info = zf.getinfo(filename)
            # Check if file has execute bit set
            unix_mode = info.external_attr >> 16
            if unix_mode and (unix_mode & 0o111):
                executable_files.append(filename)
                report.add_info(f"Python file has execute permission: {filename}")
    
    if executable_files:
        print(f"  ℹ️  Found {len(executable_files)} .py files with execute permissions")
    else:
        print("  ✅ No unnecessary execute permissions")
    
    # 2. Check for proper UTF-8 encoding
    encoding_issues = []
    for filename in files:
        if filename.endswith('.py'):
            try:
                content = zf.read(filename)
                content.decode('utf-8')
            except UnicodeDecodeError as e:
                encoding_issues.append(filename)
                report.add_error(f"UTF-8 encoding error in {filename}: {e}", "linux")
    
    if encoding_issues:
        print(f"  ❌ Found {len(encoding_issues)} files with encoding issues")
    else:
        print("  ✅ All Python files are valid UTF-8")
        report.add_info("All files use UTF-8 encoding")
    
    report.stats['linux_checks'] = 2

def check_python_code_quality(files, zf, report, verbose=False):
    """Exhaustive Python code quality checks."""
    print("\n🐍 Checking Python Code Quality...")
    
    stats = {
        'files_checked': 0,
        'total_lines': 0,
        'import_errors': 0,
        'syntax_errors': 0,
        'encoding_declarations': 0,
    }
    
    for filename in files:
        if not filename.endswith('.py'):
            continue
            
        stats['files_checked'] += 1
        
        try:
            content = zf.read(filename).decode('utf-8')
            lines = content.split('\n')
            stats['total_lines'] += len(lines)
            
            # 1. Check for encoding declaration (optional but good practice)
            if any(re.match(r'#.*coding[:=]\s*([-\w.]+)', line) for line in lines[:2]):
                stats['encoding_declarations'] += 1
            
            # 2. Check for syntax errors by attempting to parse
            try:
                ast.parse(content, filename=filename)
                if verbose:
                    print(f"  ✅ {filename}: Valid Python syntax")
            except SyntaxError as e:
                stats['syntax_errors'] += 1
                report.add_error(
                    f"Syntax error in {filename} line {e.lineno}: {e.msg}",
                    "python"
                )
                print(f"  ❌ {filename}: Syntax error")
            
            # 3. Check for problematic imports
            wildcard_imports = [i+1 for i, line in enumerate(lines) 
                              if re.match(r'^\s*from .* import \*', line)]
            if wildcard_imports:
                report.add_warning(
                    f"{filename}: Wildcard import on line(s) {wildcard_imports} "
                    "(not PEP8 compliant)",
                    "python"
                )
                stats['import_errors'] += 1
            
            # 4. Check for relative imports without fallback protection
            relative_imports = [i+1 for i, line in enumerate(lines)
                              if re.match(r'^\s*from \.(\.?)\s+import', line)]
            if relative_imports and 'init' not in filename:
                report.add_info(
                    f"{filename}: Uses relative imports on line(s) {relative_imports}"
                )
            
            # 5. Check for line endings consistency
            if '\r\n' in content and '\n' in content.replace('\r\n', ''):
                report.add_warning(
                    f"{filename}: Mixed line endings (CRLF and LF)",
                    "python"
                )
            elif '\r\n' in content:
                report.add_info(f"{filename}: Uses Windows line endings (CRLF)")
            
            # 6. Check for tabs vs spaces
            has_tabs = any('\t' in line for line in lines)
            has_spaces = any(re.match(r'^[ ]+\S', line) for line in lines)
            if has_tabs and has_spaces:
                report.add_warning(
                    f"{filename}: Mixed tabs and spaces (not PEP8 compliant)",
                    "python"
                )
            
            # 7. Check for very long lines (PEP8 suggests 79, we'll warn at 120)
            long_lines = [(i+1, len(line)) for i, line in enumerate(lines) if len(line) > 120]
            if long_lines and verbose:
                report.add_info(
                    f"{filename}: Has {len(long_lines)} lines exceeding 120 characters"
                )
            
        except UnicodeDecodeError as e:
            report.add_error(f"Cannot decode {filename}: {e}", "python")
        except Exception as e:
            report.add_warning(f"Error analyzing {filename}: {e}", "python")
    
    print(f"  ✅ Checked {stats['files_checked']} Python files")
    print(f"  ℹ️  Total lines of code: {stats['total_lines']}")
    if stats['syntax_errors'] == 0:
        print(f"  ✅ No syntax errors found")
        report.add_info("All Python files have valid syntax")
    else:
        print(f"  ❌ Found {stats['syntax_errors']} files with syntax errors")
    
    if stats['import_errors'] > 0:
        print(f"  ⚠️  Found {stats['import_errors']} files with wildcard imports")
    
    report.stats.update(stats)

def check_blender_addon_structure(files, zf, report, verbose=False):
    """Exhaustive Blender addon structure validation."""
    print("\n🎨 Checking Blender Addon Structure...")
    
    # 1. Verify addon folder exists
    addon_root = None
    for f in files:
        if '/' in f:
            addon_root = f.split('/')[0]
            break
    
    if not addon_root:
        report.add_error("ZIP must contain an addon folder at root", "blender")
        return
    
    print(f"  ✅ Addon folder: {addon_root}/")
    
    # 2. Check for art_director.py
    init_path = f'{addon_root}/art_director.py'
    if init_path not in files:
        report.add_error(f"Missing {init_path}", "blender")
        print(f"  ❌ Missing art_director.py")
        return
    
    print(f"  ✅ Found art_director.py")
    
    # 3. Deep analysis of art_director.py
    try:
        init_content = zf.read(init_path).decode('utf-8')
        
        # Parse bl_info
        bl_info_match = re.search(
            r'bl_info\s*=\s*\{([^}]+)\}',
            init_content,
            re.DOTALL
        )
        
        if not bl_info_match:
            report.add_error("Missing or malformed bl_info in art_director.py", "blender")
            print("  ❌ Missing bl_info")
                else:
            print("  ✅ Found bl_info")
            
            # Extract bl_info fields
            bl_info_str = bl_info_match.group(0)
            required_fields = ['name', 'author', 'version', 'blender', 'category']
            optional_fields = ['description', 'location', 'warning', 'doc_url', 'support']
            
            for field in required_fields:
                if f'"{field}"' in bl_info_str or f"'{field}'" in bl_info_str:
                    if verbose:
                        print(f"    ✅ bl_info has '{field}'")
                            else:
                    report.add_error(f"bl_info missing required field: '{field}'", "blender")
                    print(f"    ❌ bl_info missing '{field}'")
            
            for field in optional_fields:
                if f'"{field}"' in bl_info_str or f"'{field}'" in bl_info_str:
                    if verbose:
                        print(f"    ✅ bl_info has '{field}' (optional)")
            
            # Check blender version format
            version_match = re.search(r'["\']blender["\']\s*:\s*\((\d+),\s*(\d+),\s*(\d+)\)', bl_info_str)
            if version_match:
                major, minor, patch = version_match.groups()
                print(f"    ✅ Requires Blender {major}.{minor}.{patch}+")
                report.add_info(f"Target Blender version: {major}.{minor}.{patch}+")
            else:
                report.add_warning("Cannot parse Blender version requirement", "blender")
        
        # Check for register() function
        if 'def register(' in init_content:
            print("  ✅ Found register() function")
        else:
            report.add_error("Missing register() function in art_director.py", "blender")
            print("  ❌ Missing register() function")
        
        # Check for unregister() function
        if 'def unregister(' in init_content:
            print("  ✅ Found unregister() function")
        else:
            report.add_error("Missing unregister() function in art_director.py", "blender")
            print("  ❌ Missing unregister() function")
        
        # Check for macOS import fallback system
        has_fallback = (
            'types.ModuleType' in init_content and 
            'sys.modules' in init_content
        )
        if has_fallback:
            print("  ✅ macOS import fallback system detected")
            report.add_info("Has macOS relative import fallback")
        else:
            report.add_warning(
                "No macOS import fallback detected (may fail on macOS if using relative imports)",
                "blender"
            )
            print("  ⚠️  No macOS import fallback")
        
        # Check for proper imports
        if 'import bpy' not in init_content:
            report.add_warning("art_director.py doesn't import bpy", "blender")
        
        # Check for __name__ == "__main__" guard
        if 'if __name__ == "__main__":' in init_content:
            report.add_info("Has __main__ guard (good for testing)")
        
    except Exception as e:
        report.add_error(f"Error analyzing art_director.py: {e}", "blender")
    
    # 4. Check for required modules
    required_modules = ['ui_panel.py', 'prefs.py', 'utils.py', 'workspace_setup.py',
                       'runcomfy_client.py', 'runcomfy_deployment.py', 'runcomfy_polling.py']
    
    print(f"\n  📋 Checking required modules:")
    for module in required_modules:
        module_path = f'{addon_root}/{module}'
        if module_path in files:
            print(f"    ✅ {module}")
        else:
            report.add_error(f"Missing required module: {module}", "blender")
            print(f"    ❌ {module} (missing)")
    
    # 5. Check for common optional files
    optional_files = ['README.md', 'LICENSE', 'requirements.txt']
    print(f"\n  📋 Checking optional files:")
    for fname in optional_files:
        fpath = f'{addon_root}/{fname}'
        if fpath in files:
            print(f"    ✅ {fname}")
        else:
            if fname == 'README.md':
                report.add_warning(f"Missing {fname} (recommended)", "blender")
            print(f"    ℹ️  {fname} (optional, not found)")

def check_cache_and_junk_files(files, report):
    """Check for files that shouldn't be in the package."""
    print("\n🗑️  Checking for Cache and Junk Files...")
    
    junk_patterns = [
        (r'__pycache__', 'Python cache directories'),
        (r'\.pyc$', 'Python bytecode files'),
        (r'\.pyo$', 'Python optimized bytecode'),
        (r'\.pyd$', 'Python DLL files'),
        (r'\.so$', 'Shared object files'),
        (r'\.dylib$', 'macOS dynamic libraries'),
        (r'\.dll$', 'Windows DLL files'),
        (r'\.git/', 'Git repository data'),
        (r'\.svn/', 'SVN repository data'),
        (r'\.hg/', 'Mercurial repository data'),
        (r'\.idea/', 'IDE configuration'),
        (r'\.vscode/', 'VSCode configuration'),
        (r'\.pytest_cache', 'Pytest cache'),
        (r'\.coverage', 'Coverage data'),
        (r'\.tox/', 'Tox testing'),
        (r'dist/', 'Distribution builds'),
        (r'build/', 'Build artifacts'),
        (r'\.egg-info/', 'Python egg info'),
        (r'~$', 'Backup files'),
        (r'\.bak$', 'Backup files'),
        (r'\.tmp$', 'Temporary files'),
        (r'\.swp$', 'Vim swap files'),
        (r'\.swo$', 'Vim swap files'),
        (r'Thumbs\.db$', 'Windows thumbnail cache'),
        (r'desktop\.ini$', 'Windows desktop config'),
    ]
    
    found_junk = defaultdict(list)
    for filename in files:
        for pattern, description in junk_patterns:
            if re.search(pattern, filename):
                found_junk[description].append(filename)
                break
    
    if found_junk:
        print(f"  ⚠️  Found {sum(len(v) for v in found_junk.values())} junk files")
        for description, file_list in found_junk.items():
            print(f"    • {description}: {len(file_list)} file(s)")
            report.add_warning(f"Found {len(file_list)} {description}", "cleanup")
            for f in file_list[:2]:  # Show first 2 examples
                report.add_warning(f"    {f}", "cleanup")
            if len(file_list) > 2:
                report.add_warning(f"    ... and {len(file_list) - 2} more", "cleanup")
    else:
        print("  ✅ No cache or junk files found")
        report.add_info("Package is clean (no cache/junk files)")
    
    report.stats['junk_files'] = sum(len(v) for v in found_junk.values())

def generate_statistics(files, zf, report):
    """Generate detailed package statistics."""
    print("\n📊 Package Statistics:")
    
    stats = {
        'total_files': len(files),
        'python_files': len([f for f in files if f.endswith('.py')]),
        'markdown_files': len([f for f in files if f.endswith('.md')]),
        'json_files': len([f for f in files if f.endswith('.json')]),
        'other_files': 0,
        'total_size': 0,
        'largest_file': (None, 0),
    }
    
            for filename in files:
                    info = zf.getinfo(filename)
        stats['total_size'] += info.file_size
        
        if info.file_size > stats['largest_file'][1]:
            stats['largest_file'] = (filename, info.file_size)
        
        if not any(filename.endswith(ext) for ext in ['.py', '.md', '.json']):
            stats['other_files'] += 1
    
    print(f"  • Total files: {stats['total_files']}")
    print(f"  • Python files: {stats['python_files']}")
    print(f"  • Markdown files: {stats['markdown_files']}")
    print(f"  • JSON files: {stats['json_files']}")
    print(f"  • Other files: {stats['other_files']}")
    print(f"  • Total size: {stats['total_size'] / 1024:.1f} KB")
    print(f"  • Largest file: {stats['largest_file'][0]} ({stats['largest_file'][1] / 1024:.1f} KB)")
    
    report.stats.update(stats)
    
    # Calculate compression ratio
    total_compressed = sum(zf.getinfo(f).compress_size for f in files)
    compression_ratio = (1 - total_compressed / stats['total_size']) * 100 if stats['total_size'] > 0 else 0
    print(f"  • Compression ratio: {compression_ratio:.1f}%")
    report.stats['compression_ratio'] = compression_ratio

def validate_addon_zip(zip_path, verbose=False):
    """Exhaustive validation of addon ZIP structure."""
    report = ValidationReport()
    
    report.print_section(f"VALIDATING: {os.path.basename(zip_path)}")
    
    if not os.path.exists(zip_path):
        report.add_error(f"File not found: {zip_path}", "general")
        return report
    
    print(f"📦 Opening ZIP file: {zip_path}")
    print(f"📏 File size: {os.path.getsize(zip_path) / 1024:.1f} KB\n")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Test ZIP integrity
            print("🔍 Testing ZIP integrity...")
            try:
                bad_file = zf.testzip()
                if bad_file:
                    report.add_error(f"Corrupt file in ZIP: {bad_file}", "general")
                    print(f"  ❌ ZIP integrity check failed: {bad_file}")
                else:
                    print("  ✅ ZIP integrity check passed")
                    report.add_info("ZIP file integrity verified")
            except Exception as e:
                report.add_error(f"ZIP integrity test failed: {e}", "general")
            
            files = zf.namelist()
            print(f"📄 Found {len(files)} files in ZIP\n")
            
            if verbose:
                print("📝 Files in package:")
                for f in files:
                    info = zf.getinfo(f)
                    print(f"  • {f} ({info.file_size} bytes)")
                print()
            
            # Run all checks
            check_blender_addon_structure(files, zf, report, verbose)
            check_macos_compatibility(files, zf, report)
            check_windows_compatibility(files, zf, report)
            check_linux_compatibility(files, zf, report)
            check_python_code_quality(files, zf, report, verbose)
            check_cache_and_junk_files(files, report)
            generate_statistics(files, zf, report)
    
    except zipfile.BadZipFile:
        report.add_error("File is not a valid ZIP archive", "general")
    except Exception as e:
        report.add_error(f"Error reading ZIP: {e}", "general")
    
    return report

def print_report(report):
    """Print comprehensive validation report."""
    
    # Group errors by category
    errors_by_cat = defaultdict(list)
    for error in report.errors:
        errors_by_cat[error['category']].append(error['msg'])
    
    # Group warnings by category
    warnings_by_cat = defaultdict(list)
    for warning in report.warnings:
        warnings_by_cat[warning['category']].append(warning['msg'])
    
    report.print_section("VALIDATION RESULTS")
    
    # Print errors
    if errors_by_cat:
        print("❌ ERRORS (Must fix before distribution):\n")
        for category, errors in sorted(errors_by_cat.items()):
            print(f"  [{category.upper()}]")
            for error in errors:
                print(f"    • {error}")
            print()
    
    # Print warnings
    if warnings_by_cat:
        print("⚠️  WARNINGS (Should review):\n")
        for category, warnings in sorted(warnings_by_cat.items()):
            print(f"  [{category.upper()}]")
            for warning in warnings:
                print(f"    • {warning}")
    print()
    
    # Print info messages
    if report.info:
        print("ℹ️  INFORMATION:\n")
        for info in report.info:
            print(f"  • {info}")
        print()
    
    # Print summary
    report.print_section("SUMMARY")
    
    total_errors = len(report.errors)
    total_warnings = len(report.warnings)
    total_issues = total_errors + total_warnings
    
    print(f"  • Total files: {report.stats.get('total_files', 0)}")
    print(f"  • Python files analyzed: {report.stats.get('files_checked', 0)}")
    print(f"  • Lines of code: {report.stats.get('total_lines', 0)}")
    print(f"  • Package size: {report.stats.get('total_size', 0) / 1024:.1f} KB")
    print(f"  • Compression: {report.stats.get('compression_ratio', 0):.1f}%")
    print()
    print(f"  • Checks performed:")
    print(f"    - macOS compatibility: {report.stats.get('macos_checks', 0)} tests")
    print(f"    - Windows compatibility: {report.stats.get('windows_checks', 0)} tests")
    print(f"    - Linux compatibility: {report.stats.get('linux_checks', 0)} tests")
    print(f"    - Python code quality: {report.stats.get('files_checked', 0)} files")
    print(f"    - Blender addon structure: ✓")
        print()
    print(f"  • Issues found:")
    print(f"    - Errors: {total_errors}")
    print(f"    - Warnings: {total_warnings}")
    print(f"    - Total: {total_issues}")
        print()
    
    # Final verdict
    report.print_section("VERDICT")
    
    if total_errors == 0 and total_warnings == 0:
        print("✅ VALIDATION PASSED!")
        print("✅ Package structure is perfect")
        print("✅ Ready for cross-platform distribution")
        print()
        print("🎉 Your addon is ready to ship!")
        print()
        return 0
    elif total_errors == 0:
        print("✅ VALIDATION PASSED (with warnings)")
        print("✅ No critical errors found")
        print("⚠️  Review warnings before distribution")
        print()
        print("💡 The package will work, but could be improved")
        print()
        return 0
    else:
        print("❌ VALIDATION FAILED")
        print(f"❌ Found {total_errors} error(s) that must be fixed")
        if total_warnings > 0:
            print(f"⚠️  Also found {total_warnings} warning(s)")
        print()
        print("🔧 Please fix the errors above before distributing")
        print()
        return 1

def main():
    print("🔍 Style Engine Addon Package Validator")
    print("   Exhaustive cross-platform validation")
    print("=" * 80)
    print()
    
    # Parse arguments
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    # Filter out flags from argv
    args = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
    
    if len(args) < 1:
        print("Usage: python validate_package.py <path_to_zip> [--verbose]")
        print()
        print("Examples:")
        print("  python validate_package.py styleengine.zip")
        print("  python validate_package.py styleengine.zip --verbose")
        print()
        print("Options:")
        print("  --verbose, -v    Show detailed analysis of each file")
        print()
        sys.exit(1)
    
    zip_path = args[0]
    
    if not os.path.exists(zip_path):
        print(f"❌ File not found: {zip_path}")
        print()
        sys.exit(1)
    
    # Run validation
    report = validate_addon_zip(zip_path, verbose=verbose)
    
    # Print results
    exit_code = print_report(report)
    
    # Provide actionable next steps
    if exit_code == 0 and len(report.errors) == 0:
        print("📋 Next Steps:")
        print("  1. Test the addon in Blender on your platform")
        print("  2. Send to testers on Windows, macOS, and Linux")
        print("  3. Verify all features work cross-platform")
        print("  4. Collect feedback before final release")
        print()
    elif exit_code == 1:
        print("📋 Recommended Actions:")
        print("  1. Fix all errors listed above")
        print("  2. Re-run this validator after fixes")
        print("  3. Consider addressing warnings for better quality")
        print("  4. Test in actual Blender environment")
        print()
    
    return exit_code

if __name__ == '__main__':
    try:
    sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

