# Prompt Refinement Feature (LLM Integration)

## Summary

Added a "Refine Prompt" button that uses a local LLM (via ComfyUI/Ollama) to enhance the main prompt text. The LLM takes the content from the `<p>` tag, applies prompt engineering rules, and returns an improved version that automatically replaces the original text in the editor.

---

## How It Works

### **1. User Workflow**

1. Write a basic prompt in the `<p>` tag:
   ```
   <p>frodo entering mordor</p>
   ```

2. Click **"Refine Prompt (LLM)"** button in the Prompt Settings panel

3. Wait a few seconds while the LLM processes

4. The text editor automatically updates with the refined prompt:
   ```
   <p>Frodo Baggins, a young hobbit with curly brown hair, cautiously entering the desolate volcanic wasteland of Mordor, dramatic cinematic composition, wide-angle shot, 35mm lens, harsh red lighting from lava flows, desaturated palette with warm orange accents, smoke and ash in the atmosphere, epic fantasy style, high detail</p>
   ```

5. Generate your image with the enhanced prompt

---

## Implementation Details

### **Workflow: PromptRefiner.json**

- **Input**: Node `7` ("Text Multiline") - receives the original `<p>` content
- **Processing**: Griptape Agent + Ollama LLM with 8 prompt engineering rules
- **Output**: Node `17` ("Griptape Run: Agent") - returns refined text

### **Operator: `WM_OT_RefinePrompt`**

**Location**: `scripts/addons/styleengine/ui_panel.py` (lines ~2251-2420)

**Process**:
1. Extract content from `<p>` tag using regex
2. Load `PromptRefiner.json` workflow
3. Patch node `7` with the original prompt text
4. Submit to ComfyUI server (GCS mode)
5. Poll for result (blocking, 60s timeout)
6. Extract refined text from node `17` output
7. Replace `<p>` content in text editor using regex
8. Text editor auto-refreshes (Blender native behavior)

### **Key Code Snippets**

**Extract `<p>` content:**
```python
p_match = re.search(r'<p>(.*?)</p>', current_content, re.DOTALL | re.IGNORECASE)
original_prompt = p_match.group(1).strip()
```

**Patch workflow:**
```python
workflow["7"]["inputs"]["text"] = original_prompt
```

**Replace `<p>` content:**
```python
new_content = re.sub(
    r'(<p>)(.*?)(</p>)',
    r'\1' + refined_text + r'\3',
    current_content,
    flags=re.DOTALL | re.IGNORECASE
)
text_block.clear()
text_block.write(new_content)
```

---

## UI Integration

### **Button Location**

**Panel**: N-panel → Style Engine → Prompt Settings
**Label**: "Refine Prompt (LLM)"
**Icon**: `SORTALPHA`

**Placement**: Below the HTML tag help text, above the main generation controls

---

## Requirements

### **1. Server Mode (GCS)**
- Feature **only works in Server mode** (self-hosted ComfyUI)
- Checks `runcomfy_deployment.is_server_mode()`
- Shows error if in Serverless mode

### **2. ComfyUI Dependencies**
- **Griptape ComfyUI nodes** installed
- **Ollama** running locally (default: `http://127.0.0.1:11434`)
- **Model**: `gemma3:4b` (configured in workflow)

### **3. Workflow File**
- `workflows/PromptRefiner.json` must exist in addon directory

---

## Error Handling

| Error | Message | Resolution |
|-------|---------|------------|
| No text block | "STYLEENGINE_Prompt text block not found" | Run Setup Workspace first |
| No `<p>` tag | "No <p> tag found in prompt text" | Add `<p>` tags to text |
| Empty `<p>` | "<p> tag is empty" | Write content inside `<p>` |
| Not Server mode | "Prompt refinement only works in Server mode" | Switch to GCS in preferences |
| Workflow missing | "PromptRefiner.json not found" | Verify workflow file exists |
| Timeout | "Prompt refinement timed out" | Check ComfyUI/Ollama status |
| No output | "Could not extract refined text" | Check workflow node structure |

---

## LLM Prompt Engineering Rules

The workflow includes 8 rules to ensure high-quality prompts:

1. **State Subject First**: Clear main subject and action
2. **Define Medium + Style**: Photography, illustration, 3D render, etc.
3. **Specify Framing**: Camera angle, composition, lens type
4. **Describe Lighting**: Time of day, light sources, atmosphere
5. **Add Material Details**: Textures, surfaces, physical properties
6. **Keep Medium Length**: 20-60 words optimal
7. **Show Don't Tell Mood**: Describe physical circumstances, not emotions
8. **Output Clean Text**: No markdown, titles, or conversational elements

---

## Example Transformations

### **Before → After**

**Input:**
```
<p>dragon</p>
```

**Output:**
```
<p>A majestic red dragon perched on a mountain cliff, fantasy illustration style, wide-angle shot from below, dramatic sunset lighting with warm orange and purple hues, detailed scales and wing texture, mist rolling through valleys below, epic cinematic composition, high detail</p>
```

---

**Input:**
```
<p>coffee cup on table</p>
```

**Output:**
```
<p>A ceramic coffee cup on a wooden table, product photography style, 45-degree overhead shot, 85mm lens, soft morning window light, cream and brown palette, steam rising from hot coffee, polished wood grain texture, minimalist composition</p>
```

---

**Input:**
```
<p>futuristic city</p>
```

**Output:**
```
<p>A sprawling futuristic metropolis with towering glass skyscrapers, 3D render in Blade Runner style, bird's-eye view perspective, neon-lit streets at night, cyan and magenta color palette, holographic advertisements floating between buildings, reflective surfaces and rain-slicked streets, dystopian atmosphere</p>
```

---

## Console Output

### **Success Flow**
```
[Refine Prompt] Original prompt: frodo entering mordor
[Refine Prompt] ✓ Loaded workflow: PromptRefiner.json
[Refine Prompt] ✓ Patched node 7 with prompt text
[Refine Prompt] Submitting to ComfyUI server...
[Refine Prompt] ✓ Queued prompt refinement (ID: 79274601...)
[Refine Prompt] Waiting... (2s/60s)
[Refine Prompt] Waiting... (4s/60s)
[Refine Prompt] ✓ Refined prompt: Frodo Baggins, a young hobbit...
[Refine Prompt] ✓ Updated text editor with refined prompt
```

### **Error Flow**
```
[Refine Prompt] ❌ Not in Server mode - feature requires direct ComfyUI connection
```

---

## Technical Notes

### **Blocking vs Async**

Current implementation is **blocking** (simple polling loop):
- Blender UI freezes during refinement (2-10 seconds typically)
- Easier to implement and debug
- Acceptable UX for infrequent manual operation

**Future Enhancement**: Convert to modal operator with async polling (like image generation)

### **Output Parsing**

The operator tries multiple strategies to extract refined text:

1. **Node 17** → `outputs["17"]["string"][0]`
2. **Node 17 (list)** → `outputs["17"][0]`
3. **Node 19** → `outputs["19"]["string"][0]`
4. **Node 19 (list)** → `outputs["19"][0]`

This handles different ComfyUI output formats.

### **Text Editor Auto-Refresh**

Blender automatically updates text editor views when you modify `bpy.data.texts`:
- No manual `bpy.ops.wm.redraw_timer()` needed
- Works across all text editor instances
- User sees change immediately

---

## Files Modified

| File | Changes |
|------|---------|
| `ui_panel.py` | Added `WM_OT_RefinePrompt` operator (~170 lines) |
| `ui_panel.py` | Added button to Prompt Settings UI |
| `ui_panel.py` | Registered operator in `classes` tuple |
| `workflows/PromptRefiner.json` | Created workflow file (existing) |
| `PROMPT_REFINEMENT_FEATURE.md` | This documentation |

---

## Testing Checklist

- [ ] Button appears in Prompt Settings panel
- [ ] Clicking button with no `<p>` tag shows error
- [ ] Clicking button with empty `<p>` shows error
- [ ] Clicking button in Serverless mode shows error
- [ ] Workflow loads successfully
- [ ] Node 7 is patched with correct prompt text
- [ ] Workflow submits to ComfyUI server
- [ ] Polling waits for result (shows "Waiting..." messages)
- [ ] Refined text is extracted from output
- [ ] Text editor updates with new content
- [ ] `<p>` tags remain intact, only content changes
- [ ] `<k>` and `<n>` tags are unaffected
- [ ] Next generation uses refined prompt

---

## Known Limitations

1. **Server Mode Only**: Requires self-hosted ComfyUI (not RunComfy serverless)
2. **Blocking Operation**: UI freezes during refinement
3. **60s Timeout**: Long prompts may timeout
4. **Ollama Required**: Must have local LLM running
5. **No Undo**: Previous prompt is lost (future: add history)

---

## Future Enhancements

### **Phase 1** (Current)
✅ Basic blocking implementation
✅ Manual button trigger
✅ Replaces `<p>` content
✅ Console feedback

### **Phase 2** (Optional)
- [ ] Async modal operator (non-blocking UI)
- [ ] Progress indicator in UI
- [ ] Undo/history (store previous versions)
- [ ] Compare before/after side-by-side
- [ ] Customize LLM parameters (temperature, model)

### **Phase 3** (Advanced)
- [ ] Refine keywords `<k>` separately
- [ ] Negative prompt suggestions
- [ ] Batch refinement (multiple prompts)
- [ ] Save/load refinement presets
- [ ] Auto-refinement toggle (on generate)

---

## Version

- **Date**: 2026-01-27
- **Version**: 0.3.7
- **Status**: Complete and ready for testing

---

## Summary

**The "Refine Prompt" feature is now live!** Users can click a button to enhance their prompts using a local LLM, with the refined text automatically replacing the original in the text editor. The implementation reuses existing infrastructure (workflow loading, server client, text editor management) and follows the established code patterns.
