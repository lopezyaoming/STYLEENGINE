#!/usr/bin/env python3
"""
Style Engine - Modern Cross-Platform Packaging Script
Creates proper ZIP with forward slashes for Windows/macOS/Linux compatibility

Features:
- Includes ALL addon files automatically
- Proper cross-platform path handling (forward slashes only)
- Excludes cache/temp files intelligently
- Never deletes source files
- Validates package structure
- Reports what's included/excluded
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

# ================================================================
# CONFIGURATION
# ================================================================

# Files/directories to EXCLUDE (never package these)
EXCLUDE_PATTERNS = {
    # Python cache
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    
    # Version control
    '.git',
    '.gitignore',
    '.svn',
    
    # IDE files
    '.vscode',
    '.idea',
    '.vs',
    
    # macOS
    '.DS_Store',
    '__MACOSX',
    '._*',  # Resource forks
    
    # Build artifacts
    'build',
    'dist',
    '*.egg-info',
    
    # Temp/backup
    '*.tmp',
    '*.bak',
    '*.swp',
    '*~',
    
    # Packaging directory itself
    'packaging',
    
    # Documentation that doesn't need to be in addon
    'docs',
    'tests',
    'examples',
}

# Required files (will warn if missing)
REQUIRED_FILES = [
    '__init__.py',  # Must have bl_info
    'README.md',
]

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def should_exclude(path: Path, base_dir: Path) -> bool:
    """Check if file/directory should be excluded from package."""
    
    # Get relative path
    try:
        rel_path = path.relative_to(base_dir)
    except ValueError:
        return True
    
    # Check each part of the path
    for part in rel_path.parts:
        # Exact matches
        if part in EXCLUDE_PATTERNS:
            return True
        
        # Pattern matches
        for pattern in EXCLUDE_PATTERNS:
            if '*' in pattern:
                # Simple wildcard matching
                if pattern.startswith('*'):
                    if part.endswith(pattern[1:]):
                        return True
                elif pattern.endswith('*'):
                    if part.startswith(pattern[:-1]):
                        return True
    
    return False


def get_addon_files(source_dir: Path) -> tuple[list[Path], list[str]]:
    """
    Get all files to include in addon package.
    
    Returns:
        (files_to_include, excluded_items)
    """
    files_to_include = []
    excluded_items = []
    
    for root, dirs, files in os.walk(source_dir):
        root_path = Path(root)
        
        # Filter directories (modify in place to prevent traversal)
        dirs_to_remove = []
        for d in dirs:
            dir_path = root_path / d
            if should_exclude(dir_path, source_dir):
                dirs_to_remove.append(d)
                excluded_items.append(f"{dir_path.relative_to(source_dir)}/")
        
        for d in dirs_to_remove:
            dirs.remove(d)
        
        # Filter files
        for f in files:
            file_path = root_path / f
            
            if should_exclude(file_path, source_dir):
                excluded_items.append(str(file_path.relative_to(source_dir)))
            else:
                files_to_include.append(file_path)
    
    return files_to_include, excluded_items


def create_zip_with_forward_slashes(output_zip: Path, source_dir: Path, files: list[Path]) -> bool:
    """
    Create ZIP with forward slashes for cross-platform compatibility.
    
    Args:
        output_zip: Output ZIP file path
        source_dir: Source directory (styleengine/)
        files: List of files to include
    
    Returns:
        True if successful
    """
    addon_name = source_dir.name
    
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(files):
                # Get relative path from source directory
                rel_path = file_path.relative_to(source_dir)
                
                # CRITICAL: Convert to forward slashes for cross-platform compatibility
                # Use PurePosixPath to ensure forward slashes even on Windows
                from pathlib import PurePosixPath
                posix_rel_path = PurePosixPath(rel_path)
                
                # Create archive name with addon directory prefix
                arcname = f"{addon_name}/{posix_rel_path}"
                
                # Add to ZIP
                zf.write(file_path, arcname)
        
        return True
    
    except Exception as e:
        print(f"ERROR creating ZIP: {e}")
        return False


def verify_zip_structure(zip_path: Path) -> tuple[bool, list[str]]:
    """
    Verify ZIP has correct structure and no backslashes.
    
    Returns:
        (is_valid, issues)
    """
    issues = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            entries = zf.namelist()
            
            if not entries:
                issues.append("ZIP is empty!")
                return False, issues
            
            # Check for backslashes (Windows path separators)
            backslash_entries = [e for e in entries if '\\' in e]
            if backslash_entries:
                issues.append(f"Found {len(backslash_entries)} entries with backslashes (macOS incompatible):")
                for entry in backslash_entries[:5]:
                    issues.append(f"  - {entry}")
                return False, issues
            
            # Check for proper structure (all files in addon directory)
            addon_name = Path(entries[0]).parts[0] if entries else None
            if not addon_name:
                issues.append("Cannot determine addon name from ZIP structure")
                return False, issues
            
            # All entries should start with addon name
            invalid_entries = [e for e in entries if not e.startswith(f"{addon_name}/")]
            if invalid_entries:
                issues.append(f"Found {len(invalid_entries)} entries outside addon directory:")
                for entry in invalid_entries[:5]:
                    issues.append(f"  - {entry}")
            
            # Check for required files
            entry_names = {Path(e).name for e in entries}
            missing_required = [f for f in REQUIRED_FILES if f not in entry_names]
            if missing_required:
                issues.append(f"Missing required files: {', '.join(missing_required)}")
        
        return len(issues) == 0, issues
    
    except Exception as e:
        issues.append(f"Error reading ZIP: {e}")
        return False, issues


# ================================================================
# MAIN PACKAGING FUNCTION
# ================================================================

def package_addon():
    """Main packaging function."""
    
    print("=" * 70)
    print("  Style Engine - Modern Addon Packaging")
    print("=" * 70)
    print()
    
    # Determine paths
    script_dir = Path(__file__).parent.absolute()
    
    # Source is one level up from packaging dir
    addons_dir = script_dir.parent
    source_dir = addons_dir / 'styleengine'
    
    # Output ZIP in packaging directory
    output_zip = script_dir / 'styleengine.zip'
    
    print(f"Script directory: {script_dir}")
    print(f"Source directory: {source_dir}")
    print(f"Output ZIP: {output_zip}")
    print()
    
    # CRITICAL SAFETY CHECK: Prevent packaging from wrong location
    # This prevents accidental deletion if styleengine is in the wrong place
    if source_dir.parent == script_dir:
        print("=" * 70)
        print("  [CRITICAL ERROR] SAFETY CHECK FAILED!")
        print("=" * 70)
        print()
        print("The source directory should NOT be inside the packaging directory!")
        print()
        print(f"Expected location: {script_dir.parent / 'styleengine'}")
        print(f"Found location:    {source_dir}")
        print()
        print("This safety check prevents accidental deletion of the addon.")
        print("If you moved styleengine into packaging/, move it back immediately!")
        print()
        print("Correct structure:")
        print("  scripts/addons/styleengine/     <- Source files (correct)")
        print("  scripts/addons/packaging/       <- Packaging scripts (you are here)")
        print()
        return False
    
    # Validate source directory
    if not source_dir.exists():
        print(f"[ERROR] Source directory not found: {source_dir}")
        return False
    
    if not (source_dir / '__init__.py').exists():
        print(f"[ERROR] __init__.py not found in {source_dir}")
        print("   Is this the correct addon directory?")
        return False
    
    print("[OK] Source directory validated")
    print()
    
    # Get all files to include
    print("Scanning files...")
    files_to_include, excluded_items = get_addon_files(source_dir)
    
    if not files_to_include:
        print("[ERROR] No files found to package!")
        return False
    
    print(f"[OK] Found {len(files_to_include)} files to include")
    print(f"[OK] Excluded {len(excluded_items)} items")
    print()
    
    # Show what's being included
    print("Files to include:")
    print("-" * 70)
    for file_path in sorted(files_to_include):
        rel_path = file_path.relative_to(source_dir)
        size_kb = file_path.stat().st_size / 1024
        print(f"  [+] {rel_path} ({size_kb:.1f} KB)")
    print()
    
    # Show what's being excluded (summary)
    if excluded_items:
        print("Excluded items (cache/temp):")
        print("-" * 70)
        for item in sorted(excluded_items)[:10]:  # Show first 10
            print(f"  [-] {item}")
        if len(excluded_items) > 10:
            print(f"  ... and {len(excluded_items) - 10} more")
        print()
    
    # Remove old ZIP if exists
    if output_zip.exists():
        print(f"Removing old ZIP: {output_zip.name}")
        output_zip.unlink()
        print()
    
    # Create ZIP
    print("Creating ZIP archive...")
    print("Using forward slashes for cross-platform compatibility...")
    
    success = create_zip_with_forward_slashes(output_zip, source_dir, files_to_include)
    
    if not success:
        print("[ERROR] Failed to create ZIP")
        return False
    
    print("[OK] ZIP created successfully")
    print()
    
    # Verify ZIP
    print("Verifying ZIP structure...")
    is_valid, issues = verify_zip_structure(output_zip)
    
    if not is_valid:
        print("[ERROR] ZIP validation failed:")
        for issue in issues:
            print(f"  {issue}")
        print()
        print("[WARNING] Package created but has issues!")
        return False
    
    print("[OK] ZIP structure validated")
    print()
    
    # Get ZIP info
    zip_size = output_zip.stat().st_size
    zip_size_kb = zip_size / 1024
    zip_size_mb = zip_size / (1024 * 1024)
    
    # Count files in ZIP
    with zipfile.ZipFile(output_zip, 'r') as zf:
        file_count = len(zf.namelist())
    
    # Success!
    print("=" * 70)
    print("  SUCCESS! PACKAGE CREATED")
    print("=" * 70)
    print()
    print(f"Package: {output_zip.name}")
    print(f"Size: {zip_size_mb:.2f} MB ({zip_size_kb:.0f} KB)")
    print(f"Files: {file_count}")
    print(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Cross-platform compatibility: Windows / macOS / Linux")
    print()
    print("=" * 70)
    print("  INSTALLATION INSTRUCTIONS")
    print("=" * 70)
    print()
    print("1. Open Blender 4.2 or newer")
    print("2. Edit -> Preferences -> Add-ons")
    print("3. Click 'Install from Disk...'")
    print(f"4. Select: {output_zip}")
    print("5. Enable 'Style Engine' addon")
    print("6. Configure API credentials in addon preferences")
    print()
    print("Ready to distribute!")
    print()
    
    return True


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == '__main__':
    try:
        success = package_addon()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Packaging cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

