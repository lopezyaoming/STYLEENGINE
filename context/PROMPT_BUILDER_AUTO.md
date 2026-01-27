# Prompt Builder Made Automatic

## Summary

The "Enable Prompt Builder" toggle has been removed. The system now **automatically** detects HTML tags and parses them, falling back to raw text if no tags are present.

---

## Changes Made

### 1. **UI Changes** (`ui_panel.py`)

**Removed:**
- Checkbox toggle for "Enable Prompt Builder"

**Updated:**
- Help text now always visible (no longer conditional)
- Added clarification: "Without tags, raw text is used"
- Property `use_prompt_builder` now defaults to `True`

**Before:**
```
☐ Enable Prompt Builder

[Checkbox had to be manually enabled to parse tags]
```

**After:**
```
Use HTML-style tags in text editor:
<k>keywords</k> (optional)
<p>main prompt</p> (required)
<n>negative prompt</n> (optional)
Without tags, raw text is used

[Always active, no toggle needed]
```

### 2. **Logic Changes** (`workspace_setup.py`)

**Simplified prompt processing:**

**Before:**
```python
if props.use_prompt_builder:
    positive_prompt, negative_prompt = utils.process_prompt_builder(prompt_from_editor)
    # ... handle result
else:
    # Normal mode: use raw text as-is
    props.global_prompt = prompt_from_editor
```

**After:**
```python
# Always process through prompt builder (auto-detects tags)
positive_prompt, negative_prompt = utils.process_prompt_builder(prompt_from_editor)
# Automatically falls back to raw text if no tags detected
```

### 3. **Debug Instrumentation Removed**

- Removed all debug logging code from `utils.py` and `workspace_setup.py`
- Clean codebase without temporary debugging artifacts

---

## How It Works Now

### **With HTML Tags** (automatic parsing)

**Input:**
```
# Keywords
<k>concept art, 8k</k>
# Prompt
<p>futuristic city</p>
# Negative Prompt
<n>blurry</n>
```

**Output:**
- **Positive**: `"concept art, 8k, futuristic city"`
- **Negative**: `"blurry"`
- **Console**: `"✓ Prompt Builder: Built prompt from tags"`

### **Without Tags** (automatic fallback)

**Input:**
```
a beautiful landscape with mountains
```

**Output:**
- **Positive**: `"a beautiful landscape with mountains"`
- **Negative**: `""` (empty, default will be used)
- **Console**: `"✓ Using raw text as prompt"`

---

## Detection Logic

The system checks for HTML tags automatically:

```python
# In utils.py -> process_prompt_builder()
text_lower = text.lower()
has_tags = ('<k>' in text_lower or '<p>' in text_lower or '<n>' in text_lower)

if not has_tags:
    return (text.strip(), "")  # Use raw text
```

**No user action required!**

---

## Benefits

✅ **Simpler UX** - No toggle to remember  
✅ **Automatic detection** - Just write prompts naturally  
✅ **Backward compatible** - Old raw prompts still work  
✅ **Clear feedback** - Console shows which mode was used  
✅ **Less confusion** - One way to write prompts  

---

## User Experience

### New Users

1. See the template in text editor
2. Fill in the tags
3. Generate
4. **It just works™**

No need to:
- Find a hidden toggle
- Enable a feature
- Remember to turn something on

### Existing Users (Migration)

**If you had Prompt Builder disabled:**
- No change! Raw text continues to work exactly as before
- The system detects no tags and uses raw text

**If you had Prompt Builder enabled:**
- No change! Tags continue to work exactly as before
- The system detects tags and parses them

---

## Console Messages

### Tags Detected
```
[Style Engine] ✓ Prompt Builder: Built prompt from tags (31 chars)
[Style Engine]   → Positive: concept art, 8k, futuristic city...
[Style Engine]   → Negative: blurry...
```

### No Tags (Raw Text)
```
[Style Engine] ✓ Using raw text as prompt (42 chars)
[Style Engine]   → Prompt: a beautiful landscape with mountains...
```

---

## Files Modified

| File | Changes |
|------|---------|
| `ui_panel.py` | Removed toggle, always show help text |
| `workspace_setup.py` | Simplified to always call prompt builder |
| `utils.py` | Removed debug instrumentation |
| `PROMPT_BUILDER_AUTO.md` | This documentation |

---

## Technical Details

### Property Status

The `use_prompt_builder` property still exists (for backward compatibility) but:
- Defaults to `True`
- No longer shown in UI
- Always treated as `True` in code logic

### Fallback Chain

1. **Check for text** → If empty, return `("", "")`
2. **Check for tags** → If no tags, return `(text, "")`
3. **Parse tags** → If tags but no content, return `(text, "")`
4. **Build prompt** → If tags with content, return `(positive, negative)`

---

## Testing

**Test Case 1: With Tags**
- Input: `<k>8k</k><p>dragon</p><n>ugly</n>`
- Expected: Positive=`"8k, dragon"`, Negative=`"ugly"`
- Result: ✅ Works

**Test Case 2: Without Tags**
- Input: `a beautiful sunset`
- Expected: Positive=`"a beautiful sunset"`, Negative=`""`
- Result: ✅ Works

**Test Case 3: Empty Tags**
- Input: `<k></k><p></p><n></n>`
- Expected: Falls back to raw text
- Result: ✅ Works

**Test Case 4: Partial Tags**
- Input: `<p>just a prompt</p>`
- Expected: Positive=`"just a prompt"`, Negative=`""`
- Result: ✅ Works

---

## Version

- **Date**: 2026-01-27
- **Version**: 0.3.6
- **Status**: Complete and tested

---

## Summary

**The Prompt Builder is now invisible and automatic.** Users can write prompts with HTML tags or plain text—the system figures it out automatically.
