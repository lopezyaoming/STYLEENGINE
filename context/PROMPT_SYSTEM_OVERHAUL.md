# Prompt System Overhaul - HTML Tag Format

## Overview

The prompt system has been completely overhauled to use a clean, simple HTML-style tag format. The old template system with `# Tag Name:` headers has been replaced with structured HTML tags.

## New Format

### Tag Structure

```
<k>keywords here</k>
<p>main prompt here</p>
<n>negative prompt here</n>
```

### Tag Definitions

| Tag | Purpose | Required | Description |
|-----|---------|----------|-------------|
| `<k></k>` | Keywords | No | Keywords/quality tags (prepended to prompt) |
| `<p></p>` | Main Prompt | Yes | The core prompt description |
| `<n></n>` | Negative Prompt | No | Things to avoid in generation |

### Processing Logic

1. **Keywords + Prompt**: Keywords are prepended to the prompt with comma separation
   - Example: `<k>cinematic, 8k</k>` + `<p>dragon</p>` → `"cinematic, 8k, dragon"`

2. **Negative Prompt**: Sent separately to workflow Node 7 (negative prompt node)
   - Not mixed into positive prompt
   - Has default fallback if empty

## Example Usage

```
<k>
concept art, matte painting, highly detailed, 8k, masterpiece
</k>

<p>
futuristic cyberpunk city at night with neon lights,
towering skyscrapers, flying vehicles in the distance
</p>

<n>
blurry, low quality, watermark, deformed, amateur
</n>
```

**Result:**
- **Positive Prompt**: `"concept art, matte painting, highly detailed, 8k, masterpiece, futuristic cyberpunk city at night with neon lights, towering skyscrapers, flying vehicles in the distance"`
- **Negative Prompt**: `"blurry, low quality, watermark, deformed, amateur"`

## Implementation Details

### Files Modified

1. **`utils.py`**
   - `parse_prompt_tags()`: Now parses `<k>`, `<p>`, `<n>` tags using regex
   - `build_prompt_from_template()`: Simple concatenation (keywords + prompt)
   - `process_prompt_builder()`: Entry point, checks for HTML tags

2. **`ui_panel.py`**
   - Removed `WM_OT_LoadTemplates` operator class
   - Removed `WM_OT_SavePromptAsTemplate` operator class
   - Removed template UI buttons (Load/Save Template)
   - Updated UI to show tag format help text
   - Removed operators from registration list

3. **`workspace_setup.py`**
   - Added `negative_prompt` to `session.json` writing (line 505)
   - Added `negative_prompt` sync in `generate_ai_image_cloud()` (line 2083)
   - Existing code already properly sends negative to Node 7

4. **`templates/`**
   - Created `STYLEENGINE_Example.txt` with new format
   - Old templates remain but are no longer used

### Data Flow

```
Text Editor (STYLEENGINE_Prompt)
    ↓ (user writes with HTML tags)
utils.get_prompt_from_text_editor()
    ↓
utils.process_prompt_builder(text)
    ↓ (parses <k>, <p>, <n>)
utils.parse_prompt_tags(text)
    ↓
utils.build_prompt_from_template(parsed)
    ↓ (returns tuple)
(positive_prompt, negative_prompt)
    ↓
props.global_prompt = positive_prompt
props.negative_prompt = negative_prompt
    ↓
session.json
    {
      "global_prompt": "...",
      "negative_prompt": "..."
    }
    ↓
Workflow JSON
    Node 25: positive_prompt
    Node 7: negative_prompt
```

## Backward Compatibility

### Fallback Behavior

If no HTML tags are detected:
- System returns raw text as positive prompt
- Negative prompt is empty string
- User can still type freeform prompts

### Toggle

The `use_prompt_builder` toggle still exists:
- **ON**: Parses HTML tags
- **OFF**: Uses raw text directly

## Benefits

✅ **Simple**: Only 3 tags to remember  
✅ **Clean**: No complex template assembly logic  
✅ **Explicit**: Keywords and prompt are clearly separated  
✅ **Correct**: Negative prompt properly sent to workflow  
✅ **Flexible**: Can omit optional tags  
✅ **Extensible**: Ready for LLM enhancement next phase  

## Next Steps

With the clean foundation in place, the next phase will add LLM integration:
- "Enhance Prompt" button
- Send to Ollama via ComfyUI workflow
- Return enhanced version to text editor
- Iterative prompt improvement

## Testing Checklist

- [x] Parsing works with all 3 tags
- [x] Parsing works with only `<p>` tag
- [x] Parsing works with `<k>` + `<p>` tags
- [x] Negative prompt properly stored in props
- [x] Negative prompt written to session.json
- [x] Negative prompt sent to workflow Node 7
- [x] Fallback to raw text works
- [x] UI updated (no template buttons)
- [x] Example template created

## Version

- **Version**: 0.3.5
- **Date**: 2026-01-27
- **Author**: Style Engine Team
