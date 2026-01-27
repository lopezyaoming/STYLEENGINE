# 🪄 Prompt Refinement Guide

## Quick Start

### **What It Does**
Takes your simple prompt and transforms it into a detailed, professional image generation prompt using AI.

### **How to Use**

1. **Write a basic prompt** in the text editor:
   ```
   # Prompt
   <p>dragon</p>
   ```

2. **Click "Refine Prompt (LLM)"** button in the Style Engine panel

3. **Wait 2-10 seconds** (LLM is thinking)

4. **See the refined result**:
   ```
   # Prompt
   <p>A majestic red dragon perched atop a rocky cliff, fantasy illustration style, wide-angle view from below, dramatic sunset lighting with warm orange and purple hues, detailed scales and wing membranes, smoke wisps from nostrils, mist rolling through valleys below, epic cinematic composition</p>
   ```

5. **Generate your image** with the enhanced prompt!

---

## Requirements

✅ **Server Mode (GCS)** - Must be using self-hosted ComfyUI  
✅ **ComfyUI Running** - Backend must be active  
✅ **Ollama Installed** - Local LLM server  
✅ **Griptape Nodes** - ComfyUI extension installed  

**Check your setup**: Style Engine Preferences → API Backend → "GCS (Self-hosted ComfyUI)"

---

## Examples

### **Example 1: Simple → Detailed**

**Before:**
```
<p>coffee cup</p>
```

**After:**
```
<p>A ceramic coffee cup on a wooden cafe table, product photography style, 45-degree overhead angle, 85mm lens, soft morning window light from the left, warm cream and brown palette, steam rising from hot espresso, visible coffee foam art, polished wood grain texture, shallow depth of field</p>
```

---

### **Example 2: Basic Scene → Cinematic**

**Before:**
```
<p>abandoned warehouse</p>
```

**After:**
```
<p>An abandoned industrial warehouse interior, cinematic photography style, wide-angle shot from low perspective, harsh sunlight streaming through broken windows casting dramatic shadows, dusty atmosphere with visible light rays, decaying concrete and rusted metal surfaces, muted desaturated palette with warm highlights, post-apocalyptic mood</p>
```

---

### **Example 3: Character → Portrait**

**Before:**
```
<p>wizard</p>
```

**After:**
```
<p>An elderly wizard with a long white beard and pointed hat, fantasy portrait style, 3/4 view close-up, 85mm lens, warm candlelight illumination from below, deep shadows creating mysterious atmosphere, detailed fabric texture on robes, glowing staff in background, rich purple and gold color palette, wise and powerful expression</p>
```

---

## What Gets Enhanced?

The LLM adds these elements to your prompt:

✨ **Subject Details** - Specific characteristics and actions  
✨ **Medium & Style** - Photography, illustration, 3D render, etc.  
✨ **Camera & Composition** - Angle, framing, lens type  
✨ **Lighting** - Type, direction, color temperature  
✨ **Materials & Textures** - Physical properties and details  
✨ **Color Palette** - Specific color schemes and mood  
✨ **Atmosphere** - Environmental effects and mood  

---

## Important Notes

### **Only Refines `<p>` Tag**
- Keywords `<k>` are **not** changed
- Negative prompt `<n>` is **not** changed
- Only the main prompt inside `<p></p>` is enhanced

### **Manual Operation**
- You must click the button each time
- Not automatic on generation (you decide if you like the result)
- Original prompt is replaced (no undo yet)

### **Requires Internet?**
- **No!** Runs 100% locally using Ollama
- LLM model runs on your machine
- No data sent to external services

---

## Troubleshooting

### **Button Doesn't Appear**
- Reload Blender addon (F3 → "Reload Scripts")
- Check Style Engine panel is visible (press `N` in 3D viewport)

### **"Not in Server mode" Error**
- Open Preferences (Edit → Preferences → Add-ons → Style Engine)
- Set "API Backend" to "GCS (Self-hosted ComfyUI)"
- Set "Server URL" (e.g., `http://34.145.107.158:8188`)
- Click "Test Server Connection" to verify

### **"Workflow not found" Error**
- Verify `PromptRefiner.json` exists in addon's `workflows/` folder
- Reinstall addon if missing

### **"Timed out" Error**
- Check Ollama is running: `http://127.0.0.1:11434`
- Check ComfyUI console for errors
- Verify Griptape nodes are installed
- Try a shorter/simpler prompt first

### **Weird/Wrong Output**
- LLM sometimes hallucinates - click button again for new result
- Adjust your input to be more specific
- Check workflow configuration (model temperature, etc.)

---

## Tips for Best Results

### **✓ DO:**
- Start with clear, specific subjects ("red dragon" not "creature")
- Include key context ("on mountain", "in forest", "at sunset")
- Use style hints ("anime", "photorealistic", "concept art")
- Keep input focused (1-5 words usually ideal)

### **✗ DON'T:**
- Write long paragraphs (LLM will condense them)
- Include negative prompts in `<p>` (use `<n>` tag instead)
- Use vague terms ("something cool", "interesting thing")
- Mix multiple unrelated subjects

---

## Advanced: Customizing the LLM

Edit `workflows/PromptRefiner.json` to customize:

- **Model**: Change `gemma3:4b` to other Ollama models
- **Temperature**: Adjust creativity (0.0-1.0)
- **Rules**: Modify prompt engineering guidelines
- **Length**: Target word count

**Node 3**: Ollama configuration  
**Nodes 4-18**: Prompt engineering rules  

---

## Keyboard Shortcut (Future)

Currently manual button only.

Planned: `Alt+R` to refine prompt in text editor.

---

## Version

- **Added**: 2026-01-27
- **Version**: 0.3.7
- **Status**: Production ready

---

**Happy prompting!** 🎨✨
