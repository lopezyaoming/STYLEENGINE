# Prompt Builder - User Guide

## Overview

**Prompt Builder** is an optional feature that helps you create perfect SDXL prompts using a simple, predictable template system.

### Key Features:
✅ **NO external dependencies** - Pure Python, no AI, no complexity  
✅ **Simple HTML-like tags** - Easy to learn and use  
✅ **Predictable output** - Same input always gives same output  
✅ **Optional** - Works alongside normal prompting  
✅ **Fallback safe** - If no tags found, uses raw text  

---

## How to Enable

1. Open **3D View → Sidebar → Style Engine**
2. Find the **"Prompt Settings"** box
3. Check **"Enable Prompt Builder"**
4. The helper text will appear showing available tags

---

## Using Tags

Write your prompt in the **STYLEENGINE_Prompt** text editor using HTML-like tags:

### Basic Example:

```
<subject>futuristic city skyline</subject>
<style>cinematic illustration, concept art</style>
<details>flying cars and holographic billboards</details>
<environment>nighttime metropolis, neon-lit streets</environment>
<mood>bright, optimistic future vibe</mood>
<camera>wide-angle shot from a rooftop</camera>
<lighting>vibrant neon lights and soft moonlight</lighting>
<negative_prompt>blurry, low-res, watermark</negative_prompt>
```

### Result:

```
Cinematic illustration, concept art of futuristic city skyline with flying cars and holographic billboards, in nighttime metropolis, neon-lit streets. Bright, optimistic future vibe atmosphere. Wide-angle shot from a rooftop perspective; lit by vibrant neon lights and soft moonlight.
```

---

## Available Tags

| Tag | Description | Example |
|-----|-------------|---------|
| `<subject>` | Main focal point | `medieval knight` |
| `<style>` | Art style and medium | `photo, oil painting, 3D render` |
| `<details>` | Specific actions/features | `holding a sword, wearing armor` |
| `<environment>` | Background setting | `in a castle courtyard, sunset` |
| `<mood>` | Atmosphere | `dramatic, mysterious` |
| `<camera>` | Perspective/angle | `low-angle hero shot` |
| `<lighting>` | Light conditions | `golden hour lighting` |
| `<negative_prompt>` | Things to avoid | `blurry, watermark, text` |

---

## Tag Rules

### Format:
```
<tagname>content goes here</tagname>
```

### Rules:
- ✅ Tags are **case-insensitive** (`<Subject>` = `<subject>`)
- ✅ **Whitespace is cleaned** - extra spaces/newlines removed
- ✅ **Order doesn't matter** - tags can be in any order
- ✅ **Optional tags** - use only the tags you need
- ✅ **Commas allowed** - you can use commas in content
- ❌ **No nesting** - don't put tags inside other tags
- ❌ **Must close** - every `<tag>` needs `</tag>`

---

## Examples

### Example 1: Simple Portrait

**Input:**
```
<subject>young woman</subject>
<style>photorealistic portrait</style>
<mood>serene, peaceful</mood>
<lighting>soft natural window light</lighting>
```

**Output:**
```
Photorealistic portrait of young woman. Serene, peaceful atmosphere; lit by soft natural window light.
```

---

### Example 2: Fantasy Scene

**Input:**
```
<subject>dragon perched on mountaintop</subject>
<details>breathing fire, scales glinting</details>
<environment>snowy peaks, stormy sky</environment>
<style>fantasy art, digital painting</style>
<mood>epic, powerful</mood>
<camera>dramatic low angle</camera>
<lighting>lightning illuminating the scene</lighting>
<negative_prompt>cartoon, anime style</negative_prompt>
```

**Output:**
```
Fantasy art, digital painting of dragon perched on mountaintop with breathing fire, scales glinting, in snowy peaks, stormy sky. Epic, powerful atmosphere. Dramatic low angle perspective; lit by lightning illuminating the scene.
```

---

### Example 3: Product Shot

**Input:**
```
<subject>luxury watch</subject>
<style>commercial photography, 8K, ultra HD</style>
<environment>on marble surface, minimal background</environment>
<camera>macro shot, shallow depth of field</camera>
<lighting>studio lighting, rim light</lighting>
```

**Output:**
```
Commercial photography, 8K, ultra HD of luxury watch, in on marble surface, minimal background. Macro shot, shallow depth of field perspective; lit by studio lighting, rim light.
```

---

## How It Works (Under the Hood)

### 1. Parse Tags
- Finds all `<tag>content</tag>` pairs
- Extracts content for each tag
- Cleans whitespace

### 2. Build Prompt
Simple connectors are used to join the parts:
```
[Style] of [Subject] with [Details], in [Environment]. 
[Mood] atmosphere. [Camera] perspective; lit by [Lighting].
```

### 3. Fallback
- If no tags found → uses raw text as-is
- If tags found but empty → skips that part
- Always produces valid output

---

## Switching Between Modes

### Normal Mode (Prompt Builder OFF):
- Write prompts normally in text editor
- Text sent to AI exactly as written
- Full manual control

### Template Mode (Prompt Builder ON):
- Write prompts with tags
- Tags automatically converted to coherent prompt
- Structured and predictable

**You can switch anytime!** The checkbox instantly changes the behavior.

---

## Tips & Best Practices

### ✅ DO:
- Use descriptive, specific content
- Experiment with different combinations
- Keep tags organized (one line per tag is easier to read)
- Use commas to separate multiple descriptors
- Test with simple prompts first

### ❌ DON'T:
- Nest tags inside other tags
- Forget to close tags
- Use special characters in tag names
- Over-complicate - simple is better!

---

## Troubleshooting

### "Prompt Builder: No tags found"
**Cause:** No valid tags detected in text  
**Solution:**  
- Check tags are properly formatted: `<tag>content</tag>`
- Ensure tags are closed
- Make sure there are no typos in tag names

### Output looks weird
**Cause:** Missing key tags like `subject` or `style`  
**Solution:**  
- At minimum, include `<subject>` and `<style>`
- More tags = better structure

### Tags not working
**Cause:** Prompt Builder not enabled  
**Solution:**  
- Check the checkbox in UI is ON
- Look for "✓ Prompt Builder" message in console

---

## Console Feedback

When Prompt Builder is active, you'll see:

```
[Style Engine] ✓ Prompt Builder: Built prompt from tags (234 chars)
[Style Engine]   → Cinematic illustration of futuristic city...
```

When disabled or no tags found:

```
[Style Engine] ✓ Auto-synced prompt from text editor (156 chars)
```

---

## Advanced: Tag-Free Sections

You can mix tags with free-form text:

```
Note to AI: This is a test render

<subject>robot</subject>
<style>3D render</style>

(Adding some extra notes here)
```

**Only the tagged content will be processed** into the structured prompt.

---

## Future Enhancements

The simple structure enables future upgrades:
- 🔮 Template presets (save/load common setups)
- 🔮 LLM expansion (AI enhances your prompts)
- 🔮 Team templates (share across projects)
- 🔮 Auto-suggestions based on scene

But for now, it's **simple, predictable, and works!**

---

## FAQ

**Q: Do I have to use all tags?**  
A: No! Use only what you need. Subject and Style are recommended minimum.

**Q: Can I use the same tag multiple times?**  
A: The parser will use the last occurrence. Better to combine in one tag with commas.

**Q: What happens to the negative prompt?**  
A: Currently stored but not sent to SDXL workflow. Reserved for future use.

**Q: Can I save my tag templates?**  
A: Not yet! This is planned for a future update. For now, save your favorite templates in a text file.

**Q: Does this work with reference images?**  
A: Yes! Prompt Builder works alongside all other Style Engine features.

**Q: Is there a performance impact?**  
A: No! Parsing is instant (< 1ms). Zero overhead.

---

## Summary

**Prompt Builder helps you create consistent, professional prompts using a simple template system.**

- ✅ Optional checkbox to enable
- ✅ Simple HTML-like tag format
- ✅ NO external dependencies
- ✅ Predictable, repeatable results
- ✅ Works with existing workflow
- ✅ Fallback to normal mode if no tags

**Try it out and see how it streamlines your prompting!** 🎨

---

*For technical details, see PROMPT_BUILDER_TECHNICAL.md*

