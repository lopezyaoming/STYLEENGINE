# Comment-Style Format Migration
**Date:** November 17, 2025  
**Status:** ✅ IMPLEMENTED  
**Breaking Change:** Yes - old HTML-style templates won't work

---

## 🎯 **WHAT CHANGED**

### ❌ **Old Format (HTML-style)**
```
<subject>futuristic city skyline</subject>
<style>cinematic illustration, concept art</style>
<details>flying cars and holographic billboards</details>
<environment>nighttime metropolis, neon-lit streets</environment>
<mood>bright, optimistic future vibe</mood>
<camera>wide-angle shot from a rooftop perspective</camera>
<lighting>vibrant neon lights and soft moonlight</lighting>
<negative_prompt>blurry, low-res, watermark, text</negative_prompt>
```

**Issues:**
- ❌ Cluttered, hard to scan
- ❌ No syntax highlighting
- ❌ Looks like XML/HTML code
- ❌ Closing tags required (verbose)
- ❌ Not intuitive for artists

---

### ✅ **New Format (Comment-style)**
```python
# Subject:
futuristic city skyline

# Style:
cinematic illustration, concept art, ArtStation quality

# Details:
flying cars and holographic billboards

# Environment:
nighttime metropolis, neon-lit streets

# Mood:
bright, optimistic future vibe

# Camera:
wide-angle shot from a rooftop perspective

# Lighting:
vibrant neon lights and soft moonlight

# Negative Prompt:
blurry, low-res, watermark, text
```

**Benefits:**
- ✅ Clean, easy to scan
- ✅ Syntax highlighting (Python/Markdown)
- ✅ Looks professional in text editor
- ✅ No closing tags needed
- ✅ Natural for artists
- ✅ Works in Blender's text editor perfectly

---

## 🔧 **IMPLEMENTATION**

### Parser Change (utils.py)

**Old Regex:**
```python
pattern = r'<(\w+)>(.*?)</\1>'  # Matches <tag>content</tag>
```

**New Regex:**
```python
pattern = r'#\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*:\s*\n(.*?)(?=\n#|\Z)'
```

**What it matches:**
```
#\s*               # Hash with optional spaces
([A-Za-z]+...)     # Tag name (can be multi-word like "Negative Prompt")
\s*:\s*\n          # Optional spaces, colon, optional spaces, newline
(.*?)              # Content (non-greedy)
(?=\n#|\Z)         # Until next # header or end of string
```

**Flexible Spacing:**
- `#Subject:` ✅
- `# Subject:` ✅
- `#  Subject:` ✅
- `# Subject  :` ✅
- `# Subject :` ✅

**Multi-word Tags:**
- `# Negative Prompt:` → `negative_prompt` ✅
- `# Camera Angle:` → `camera_angle` ✅

---

## 📊 **TEST RESULTS**

### Full Test Case:
```python
# Subject:
futuristic city skyline

# Style:
cinematic illustration, concept art, ArtStation quality

# Details:
flying cars and holographic billboards

# Environment:
nighttime metropolis, neon-lit streets

# Mood:
bright, optimistic future vibe

# Camera:
wide-angle shot from a rooftop perspective

# Lighting:
vibrant neon lights and soft moonlight

# Negative Prompt:
blurry, low-res, watermark, text
```

**Parsed Output:**
```
subject              => futuristic city skyline
details              => flying cars and holographic billboards
environment          => nighttime metropolis, neon-lit streets
mood                 => bright, optimistic future vibe
style                => cinematic illustration, concept art, ArtStation quality
camera               => wide-angle shot from a rooftop perspective
lighting             => vibrant neon lights and soft moonlight
negative_prompt      => blurry, low-res, watermark, text
```

✅ **All 8 tags parsed correctly!**

---

### Edge Cases:

**Spacing Variations:**
```python
#Subject:
dragon

#  Style:
fantasy art

# Details  :
breathing fire

#Mood:
epic
```

**Result:** ✅ All parsed correctly (flexible spacing)

**Empty Lines:**
```python
# Subject:
robot warrior


# Style:
sci-fi concept art


# Mood:
dramatic
```

**Result:** ✅ All parsed correctly (handles empty lines)

---

## 🎨 **VISUAL IMPROVEMENT**

### In Blender's Text Editor:

#### Old (HTML-style):
```
<subject>dragon</subject><style>fantasy</style>
```
- White text on dark background
- No visual hierarchy
- Hard to distinguish tags from content

#### New (Comment-style):
```python
# Subject:
dragon

# Style:
fantasy
```
- **`#` headers** are syntax highlighted (usually gray/green)
- Content is plain text (white)
- Clear visual separation
- Matches Python/Markdown conventions

---

## 📚 **DOCUMENTATION UPDATES NEEDED**

### Files to Update:

1. ✅ `utils.py` - Parser function (DONE)
2. ⏳ `PROMPT_BUILDER_GUIDE.md` - User guide
3. ⏳ `PROMPT_BUILDER_TECHNICAL.md` - Technical docs
4. ⏳ `PROMPT_BUILDER_EXAMPLES.txt` - Example templates
5. ⏳ All template files in `templates/` folder:
   - `STYLEENGINE_Cinematic_Scene.txt`
   - `STYLEENGINE_Fantasy_Dragon.txt`
   - `STYLEENGINE_Portrait_Photo.txt`
   - `STYLEENGINE_Product_Shot.txt`
   - `STYLEENGINE_SciFi_Robot.txt`
6. ⏳ `templates/README.md` - Template usage guide

---

## 🚀 **USER WORKFLOW**

### Creating a Prompt:

1. **Enable Prompt Builder** (checkbox in UI)
2. **Templates auto-load** into text editor
3. **Open any template** (e.g., STYLEENGINE_Cinematic_Scene)
4. **See clean format:**
   ```python
   # Subject:
   <your subject here>
   
   # Style:
   <your style here>
   ```
5. **Fill in sections** (syntax highlighting helps!)
6. **Generate** → Parser extracts tags and builds coherent prompt

---

## 🔄 **MIGRATION GUIDE**

### For Existing Templates:

**Conversion Pattern:**
```
OLD: <tag>content</tag>
NEW: # Tag:\ncontent\n
```

**Example Conversion:**

**Before:**
```
<subject>dragon</subject>
<style>fantasy art</style>
```

**After:**
```python
# Subject:
dragon

# Style:
fantasy art
```

### Automated Conversion (if needed):
```python
import re

def convert_html_to_comment(text):
    """Convert old HTML-style to new comment-style"""
    pattern = r'<(\w+)>(.*?)</\1>'
    
    def replace_tag(match):
        tag = match.group(1).replace('_', ' ').title()
        content = match.group(2).strip()
        return f"# {tag}:\n{content}\n"
    
    return re.sub(pattern, replace_tag, text, flags=re.DOTALL)
```

---

## ⚠️ **BACKWARD COMPATIBILITY**

**Breaking Change:** Old templates using `<tag>` format will NOT work.

**Mitigation:**
1. All shipped templates will be updated
2. User templates in `templates/` folder need manual update
3. Clear error message if no tags found
4. Easy conversion (copy, paste, add # and : and newlines)

---

## 🎯 **SUPPORTED TAGS**

All tags remain the same, just different syntax:

| Tag | Format | Example |
|-----|--------|---------|
| Subject | `# Subject:` | Main focal point |
| Details | `# Details:` | Specific details/actions |
| Environment | `# Environment:` | Background setting |
| Mood | `# Mood:` | Atmosphere |
| Style | `# Style:` | Art style/medium |
| Camera | `# Camera:` | Angle/perspective |
| Lighting | `# Lighting:` | Lighting conditions |
| Negative Prompt | `# Negative Prompt:` | Things to avoid |

**Note:** "Negative Prompt" with space is automatically converted to `negative_prompt` with underscore.

---

## 🧪 **TESTING**

### Manual Test in Blender:

1. Enable Prompt Builder
2. Create new text: `STYLEENGINE_Test`
3. Paste:
   ```python
   # Subject:
   test dragon
   
   # Style:
   fantasy art
   ```
4. Generate
5. Check console for parsed output

**Expected Console:**
```
[Style Engine] Prompt Builder: Built prompt from tags
[Style Engine]   → Positive: Fantasy art of test dragon.
```

---

## 📈 **PERFORMANCE**

**No performance impact!**
- Same regex engine (re module)
- Similar pattern complexity
- Slightly simpler (no closing tag backreference)

---

## 🎉 **RESULT**

**Clean, professional, intuitive prompt templates!**

Artists can now:
- ✅ Read prompts at a glance
- ✅ Use natural Python/Markdown syntax
- ✅ Benefit from syntax highlighting
- ✅ Type less (no closing tags)
- ✅ Focus on content, not formatting

**The UI experience is now visually appealing and professionally formatted!** 🎨

---

## 🔗 **RELATED FILES**

- Parser: `scripts/addons/styleengine/utils.py` (lines 434-501)
- Integration: `scripts/addons/styleengine/workspace_setup.py`
- Templates: `scripts/addons/styleengine/templates/`
- User guide: `PROMPT_BUILDER_GUIDE.md` (needs update)
- Technical: `PROMPT_BUILDER_TECHNICAL.md` (needs update)

