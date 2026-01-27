# Default Template Auto-Creation - Update

## Change Summary

Updated `get_or_create_prompt_text()` to automatically populate the STYLEENGINE_Prompt text block with the default template structure when first created.

---

## Default Template Structure

When STYLEENGINE_Prompt is created (during workspace setup or first use), it now contains:

```
# Keywords
<k></k>
# Prompt
<p></p>
# Negative Prompt
<n></n>
```

---

## Implementation

### File Modified: `utils.py`

**Function:** `get_or_create_prompt_text()`

**Before:**
```python
if text_name not in bpy.data.texts:
    text = bpy.data.texts.new(text_name)
    # Start with blank prompt - user writes their own
    print(f"[Style Engine] Created prompt text block: {text_name}")
```

**After:**
```python
if text_name not in bpy.data.texts:
    text = bpy.data.texts.new(text_name)
    
    # Write default template with HTML-style tags
    text.write("# Keywords\n")
    text.write("<k></k>\n")
    text.write("# Prompt\n")
    text.write("<p></p>\n")
    text.write("# Negative Prompt\n")
    text.write("<n></n>\n")
    
    print(f"[Style Engine] Created prompt text block: {text_name}")
```

---

## When Template is Created

The template is automatically created in these scenarios:

1. **Workspace Setup**: When user runs "Setup Workspace" operator
2. **First Use**: When `get_or_create_prompt_text()` is called and text block doesn't exist
3. **Manual Text Block Creation**: If user deletes STYLEENGINE_Prompt and it's recreated

---

## Template Examples Updated

Created/updated example templates with consistent format:

### 1. **STYLEENGINE_Minimal.txt** (NEW)
- Empty template ready to fill in
- Same structure as default

### 2. **STYLEENGINE_Example.txt** (UPDATED)
- Cyberpunk city example
- Shows proper tag usage

### 3. **STYLEENGINE_ConceptArt.txt** (NEW)
- Fantasy landscape example
- Keywords focused on concept art style

### 4. **STYLEENGINE_Photorealistic.txt** (NEW)
- Architectural interior example
- Keywords focused on photorealism

---

## User Experience

### Before
1. User runs "Setup Workspace"
2. STYLEENGINE_Prompt created but empty
3. User must manually type template structure
4. Easy to make syntax errors

### After
1. User runs "Setup Workspace"
2. STYLEENGINE_Prompt created with template
3. User sees clear structure with comments
4. User fills in between tags
5. Harder to make syntax errors

---

## Benefits

✅ **Immediate clarity** - User sees expected format  
✅ **Reduced errors** - Template shows correct structure  
✅ **Faster onboarding** - No need to memorize syntax  
✅ **Visual guide** - Comments label each section  
✅ **Ready to use** - Just fill in the blanks  

---

## Testing

**Test File:** `tests/test_template_creation.py`

**Verified:**
- ✅ All headers present (`# Keywords`, `# Prompt`, `# Negative Prompt`)
- ✅ All tags present (`<k></k>`, `<p></p>`, `<n></n>`)
- ✅ Correct order (Keywords → Prompt → Negative)
- ✅ Proper line breaks

**Test Result:** PASSED

---

## Migration

### Existing Users

If users already have a STYLEENGINE_Prompt text block:
- **No change** - Existing content is preserved
- Template only applies to NEW text blocks

If users want the template:
1. Delete existing STYLEENGINE_Prompt
2. Run "Setup Workspace" or trigger any operation that calls `get_or_create_prompt_text()`
3. New template will be created

### New Users

- Automatically get template on first workspace setup
- No action needed

---

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `utils.py` | Added template writing | +6 |
| `STYLEENGINE_Minimal.txt` | New template | +6 (new) |
| `STYLEENGINE_Example.txt` | Updated format | -15 |
| `STYLEENGINE_ConceptArt.txt` | New template | +6 (new) |
| `STYLEENGINE_Photorealistic.txt` | New template | +6 (new) |
| `test_template_creation.py` | Test script | +61 (new) |
| `DEFAULT_TEMPLATE_UPDATE.md` | This doc | (new) |

---

## Version

- **Date:** 2026-01-27
- **Version:** 0.3.5
- **Related:** Prompt System Overhaul (HTML Tags)

---

## Complete ✓

The default template is now automatically created with the correct schema structure when STYLEENGINE_Prompt text block is first initialized.
