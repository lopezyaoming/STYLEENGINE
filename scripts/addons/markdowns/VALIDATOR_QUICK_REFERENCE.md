# Package Validator - Quick Reference Card

## Usage

```bash
# Basic validation
python validate_package.py styleengine.zip

# Verbose mode (detailed file analysis)
python validate_package.py styleengine.zip --verbose
python validate_package.py styleengine.zip -v
```

## What It Checks

### ✅ Cross-Platform Compatibility

| Platform | Key Checks |
|----------|------------|
| **macOS** | Hidden files, resource forks, case conflicts, symlinks |
| **Windows** | Backslashes, reserved names, trailing spaces, path length |
| **Linux** | UTF-8 encoding, file permissions |

### ✅ Python Code Quality

- Syntax errors (AST parsing)
- Import issues (wildcards, relative imports)
- Line endings (CRLF vs LF)
- Indentation (tabs vs spaces)
- Code style (long lines)

### ✅ Blender Addon Structure

- `bl_info` validation (all required fields)
- `register()` / `unregister()` functions
- macOS import fallback system
- Required modules present
- README and documentation

### ✅ Package Cleanliness

- No cache files (`__pycache__`, `.pyc`)
- No IDE config (`.vscode`, `.idea`)
- No version control (`.git`, `.svn`)
- No build artifacts (`dist/`, `build/`)
- No OS junk (`.DS_Store`, `Thumbs.db`)

## Understanding Results

### Exit Codes
- `0` = Passed ✅
- `1` = Failed ❌

### Issue Severity
- ❌ **ERRORS** = Must fix (breaks functionality)
- ⚠️  **WARNINGS** = Should fix (quality issues)
- ℹ️  **INFO** = Good to know (informational)

### Categories
- `[MACOS]` - macOS-specific issues
- `[WINDOWS]` - Windows-specific issues
- `[LINUX]` - Linux-specific issues
- `[PYTHON]` - Python code problems
- `[BLENDER]` - Addon structure issues
- `[CLEANUP]` - Junk files
- `[GENERAL]` - ZIP integrity

## Common Issues & Fixes

### ❌ Windows backslash in path
**Problem:** `styleengine\utils.py`  
**Fix:** Use PowerShell ZIP creation (see `package_addon.bat`)

### ❌ macOS hidden file found: .DS_Store
**Problem:** macOS metadata in package  
**Fix:** Clean before packaging:
```bash
find . -name ".DS_Store" -delete
```

### ⚠️ No macOS fallback import system found
**Problem:** Relative imports will fail on macOS  
**Fix:** Add fallback in `__init__.py`:
```python
import sys
import types

def setup_module_fallback():
    if "__init__.py" in __file__:
        # Create fake modules for relative imports
        # ... fallback code ...
```

### ❌ Case conflict: 'File.py' vs 'file.py'
**Problem:** Different files with same name (different case)  
**Fix:** Rename one file to be unique

### ⚠️ Found 5 Python cache directories
**Problem:** `__pycache__` folders in ZIP  
**Fix:** Exclude when packaging:
```python
if '__pycache__' in dirname:
    continue
```

## Quick Stats Interpretation

```
• Total files: 9              # Files in the ZIP
• Python files analyzed: 8    # .py files checked
• Lines of code: 1847         # Total LOC in Python files
• Package size: 45.3 KB       # Uncompressed size
• Compression: 68.4%          # ZIP compression ratio
```

**Good compression:** 60-80% (text files)  
**Poor compression:** <40% (may have binary files)

## Integration with Build Process

### In `package_addon.bat`:
```batch
python validate_package.py "%OUTPUT_ZIP%"
if %errorlevel% neq 0 (
    echo WARNING: Validation issues found
)
```

### In CI/CD:
```yaml
- name: Validate Package
  run: python validate_package.py styleengine.zip
  # Fails build if validation fails
```

## Troubleshooting

### "File not found"
- Check ZIP file exists
- Check path is correct
- Use absolute or relative path

### "Not a valid ZIP archive"
- File may be corrupted
- Try recreating the ZIP
- Check disk space

### "Cannot read file"
- Encoding issues
- Check file is valid UTF-8
- May need to fix source files

## Best Practices

1. **Run validator before every release**
2. **Fix all errors** (not just warnings)
3. **Test on actual platforms** after validation
4. **Keep validation logs** for each release
5. **Run with `--verbose`** for detailed analysis

## Advanced Usage

### Save report to file:
```bash
python validate_package.py styleengine.zip > validation_report.txt 2>&1
```

### Check only if changed:
```bash
if git diff --quiet styleengine/; then
    echo "No changes, skipping validation"
else
    python validate_package.py styleengine.zip
fi
```

### Validate multiple packages:
```bash
for zip in *.zip; do
    echo "Validating $zip..."
    python validate_package.py "$zip"
done
```

## Symbols Reference

| Symbol | Meaning |
|--------|---------|
| ✅ | Check passed |
| ❌ | Error found |
| ⚠️ | Warning |
| ℹ️ | Information |
| 🍎 | macOS |
| 🪟 | Windows |
| 🐧 | Linux |
| 🐍 | Python |
| 🎨 | Blender |
| 📦 | Package |
| 🔍 | Testing |
| 📊 | Statistics |
| 🗑️ | Cleanup |

## Support

- **Full documentation:** `EXHAUSTIVE_VALIDATION_2025-11-05.md`
- **Packaging guide:** `package_addon.bat` comments
- **macOS fixes:** `MACOS_*_2025-11-05.md` files

---

**Pro Tip:** Run with `--verbose` once to understand what the validator checks, then use normal mode for quick validation.

