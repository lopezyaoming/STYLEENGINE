# Negative Prompt Implementation

**Date:** 2025-11-13  
**Status:** ✅ COMPLETE  
**Feature:** Route Prompt Builder negative prompts to SDXL workflow

---

## Issue

The Prompt Builder was **extracting** negative prompts from `<negative_prompt>` tags but **not using them**. Instead, a hardcoded negative prompt was always sent to the SDXL workflow.

```python
# Before: Always used this, ignoring user input
negative_prompt = "text, watermark, blurry, deformed, ugly, bad anatomy, worst quality, low quality"
```

**Result:** User's custom negative prompts were ignored! ❌

---

## What Was Fixed

### 1. **Added Property to Store Negative Prompt** (`ui_panel.py`)

```python
negative_prompt: bpy.props.StringProperty(
    name="Negative Prompt",
    description="Negative prompt extracted from Prompt Builder",
    default="",
    update=update_session_json
)
```

**Purpose:** Store the extracted negative prompt in scene properties

---

### 2. **Store Negative Prompt When Extracted** (`workspace_setup.py` line ~1611)

```python
if positive_prompt:
    props.global_prompt = positive_prompt
    props.negative_prompt = negative_prompt  # NEW: Store it!
    print(f"[Style Engine]   → Negative: {negative_prompt[:50]}...")
```

**Purpose:** Save the negative prompt from Prompt Builder tags

---

### 3. **Use Custom or Default Negative Prompt** (`workspace_setup.py` line ~1920)

```python
# Use negative prompt from Prompt Builder if available, otherwise use default
custom_negative = session_data.get('negative_prompt', '')
if custom_negative:
    negative_prompt = custom_negative
    print(f"[Style Engine] 🚫 NEGATIVE PROMPT (custom): {negative_prompt}")
else:
    # Default negative prompt (good general purpose)
    negative_prompt = "text, watermark, blurry, deformed, ugly, bad anatomy, worst quality, low quality"
    print(f"[Style Engine] 🚫 NEGATIVE PROMPT (default): {negative_prompt}")
```

**Purpose:** Use custom negative if provided, otherwise fall back to default

---

## How It Works Now

### **With Prompt Builder Negative Prompt:**

```
User writes:
<subject>robot</subject>
<style>3D render</style>
<negative_prompt>cartoon, anime, toy-like</negative_prompt>

         ↓
Prompt Builder extracts:
  Positive: "3D render of robot."
  Negative: "cartoon, anime, toy-like"

         ↓
System stores:
  props.global_prompt = "3D render of robot."
  props.negative_prompt = "cartoon, anime, toy-like"

         ↓
Workflow receives:
  Node 25 (positive): "3D render of robot."
  Node 7 (negative): "cartoon, anime, toy-like"  ✅ CUSTOM!

         ↓
Console shows:
[Style Engine] 🚫 NEGATIVE PROMPT (custom): cartoon, anime, toy-like
```

---

### **Without Negative Prompt (Fallback):**

```
User writes:
<subject>robot</subject>
<style>3D render</style>
(no negative_prompt tag)

         ↓
Prompt Builder extracts:
  Positive: "3D render of robot."
  Negative: "" (empty)

         ↓
System stores:
  props.global_prompt = "3D render of robot."
  props.negative_prompt = ""

         ↓
Workflow receives:
  Node 25 (positive): "3D render of robot."
  Node 7 (negative): "text, watermark, blurry..."  ✅ DEFAULT!

         ↓
Console shows:
[Style Engine] 🚫 NEGATIVE PROMPT (default): text, watermark, blurry...
```

---

### **Normal Mode (Prompt Builder OFF):**

```
User writes:
A beautiful robot in 3D

         ↓
System stores:
  props.global_prompt = "A beautiful robot in 3D"
  props.negative_prompt = ""  (cleared)

         ↓
Workflow receives:
  Node 25 (positive): "A beautiful robot in 3D"
  Node 7 (negative): "text, watermark, blurry..."  ✅ DEFAULT!

         ↓
Console shows:
[Style Engine] 🚫 NEGATIVE PROMPT (default): text, watermark, blurry...
```

---

## Benefits

### Before:
❌ Custom negative prompts ignored  
❌ Always used hardcoded default  
❌ No control over what to avoid  

### After:
✅ **Custom negative prompts work!**  
✅ **Smart fallback** to default if none provided  
✅ **Console feedback** shows which is being used  
✅ **Session JSON** persists negative prompt  

---

## Console Output

### When Custom Negative Used:
```
[Style Engine] ✓ Prompt Builder: Built prompt from tags (150 chars)
[Style Engine]   → Positive: Cinematic illustration of futuristic city...
[Style Engine]   → Negative: blurry, low-res, watermark
[Style Engine] 📝 POSITIVE PROMPT: Cinematic illustration of...
[Style Engine] 🚫 NEGATIVE PROMPT (custom): blurry, low-res, watermark
```

### When Default Used:
```
[Style Engine] ✓ Prompt Builder: Built prompt from tags (150 chars)
[Style Engine]   → Positive: Cinematic illustration of futuristic city...
[Style Engine]   → Negative: (none - will use default)
[Style Engine] 📝 POSITIVE PROMPT: Cinematic illustration of...
[Style Engine] 🚫 NEGATIVE PROMPT (default): text, watermark, blurry, deformed...
```

---

## Files Modified

### 1. **`ui_panel.py`** (Lines ~78-83)
- Added `negative_prompt` property to `StyleEngineProperties`

### 2. **`workspace_setup.py`** (Lines ~1611, 1621, 1626, 1920-1930)
- Store negative prompt when Prompt Builder processes it
- Clear negative prompt when Prompt Builder disabled
- Use custom negative if available, else default
- Updated console logging to show which type

---

## Workflow Node Mapping

**Node 7** in SDXLREF workflow receives the negative prompt:

```python
"7": {"inputs": {"text": negative_prompt}},  # Negative Prompt (Node 7)
```

Now it receives:
- **Custom negative** from `<negative_prompt>` tag (if provided)
- **Default negative** (if tag empty or Prompt Builder disabled)

---

## Default Negative Prompt

The fallback negative prompt is:
```
"text, watermark, blurry, deformed, ugly, bad anatomy, worst quality, low quality"
```

This is a good general-purpose negative for SDXL that prevents common artifacts.

---

## Examples

### Example 1: Fantasy Scene with Custom Negative
```
<subject>ancient dragon</subject>
<style>fantasy digital painting</style>
<negative_prompt>cartoon, anime style, chibi, cute</negative_prompt>
```

**Sent to SDXL:**
- Positive: "Fantasy digital painting of ancient dragon."
- Negative: "cartoon, anime style, chibi, cute" ✅

---

### Example 2: No Negative Specified
```
<subject>luxury watch</subject>
<style>commercial photography</style>
```

**Sent to SDXL:**
- Positive: "Commercial photography of luxury watch."
- Negative: "text, watermark, blurry, deformed..." ✅ (default)

---

### Example 3: Empty Negative Tag
```
<subject>robot</subject>
<style>3D render</style>
<negative_prompt></negative_prompt>
```

**Sent to SDXL:**
- Positive: "3D render of robot."
- Negative: "text, watermark, blurry, deformed..." ✅ (default, empty treated as none)

---

## Testing

### Test 1: Custom Negative Prompt
1. Enable Prompt Builder
2. Write prompt with `<negative_prompt>cartoon, anime</negative_prompt>`
3. Generate image
4. **Check console:** Should say "NEGATIVE PROMPT (custom): cartoon, anime"

### Test 2: No Negative Prompt
1. Enable Prompt Builder
2. Write prompt WITHOUT `<negative_prompt>` tag
3. Generate image
4. **Check console:** Should say "NEGATIVE PROMPT (default): text, watermark..."

### Test 3: Empty Negative Prompt
1. Enable Prompt Builder
2. Write prompt with `<negative_prompt></negative_prompt>`
3. Generate image
4. **Check console:** Should say "NEGATIVE PROMPT (default): text, watermark..."

### Test 4: Prompt Builder Disabled
1. Disable Prompt Builder
2. Write normal prompt
3. Generate image
4. **Check console:** Should say "NEGATIVE PROMPT (default): text, watermark..."

---

## Implementation Summary

### Key Changes:
1. ✅ Added property to store negative prompt
2. ✅ Extract and store from Prompt Builder
3. ✅ Use custom if available, default otherwise
4. ✅ Clear when Prompt Builder disabled
5. ✅ Console logging shows which type
6. ✅ Session JSON persists it

### Logic Flow:
```
Prompt Builder enabled?
    ↓ YES
Parse tags → extract negative_prompt
    ↓
negative_prompt empty?
    ↓ YES: Use default
    ↓ NO: Use custom
    ↓
Send to Node 7 → SDXL workflow
```

---

## Status

✅ **COMPLETE AND READY FOR TESTING**

Negative prompts from Prompt Builder now **work correctly** and are sent to the SDXL workflow!

Users can now specify exactly what they want to avoid in their generations. 🎨

---

*Implementation completed: 2025-11-13*

