# Style Engine - Prompt Templates

This directory contains prompt templates for the Style Engine addon's Prompt Builder feature.

---

## 📁 Available Templates

### 1. **Empty** (`STYLEENGINE_Empty.txt`)
- Blank template with all tag sections ready to fill
- Use this as a starting point for custom prompts
- All tags are empty, ready for your content

### 2. **Vizdev** (`STYLEENGINE_Vizdev.txt`)
- Visual Development / Concept Art style
- Optimized for environment design and matte painting aesthetics
- Painterly, cinematic, story-driven atmosphere
- Best for: Concept art, production design, environment exploration

### 3. **Photorealistic** (`STYLEENGINE_Photorealistic.txt`)
- Professional photography style
- Optimized for realistic, commercial-quality results
- Studio lighting and proper technical photography keywords
- Best for: Product shots, architectural photography, realistic renders

---

## 🎨 Template Format

All templates use the **comment-style tag format**:

```
# Subject:
your subject here

# Style:
art style, medium, technique

# Details:
specific details, actions, features

# Environment:
background, setting, location

# Mood:
atmosphere, feeling, emotion

# Camera:
camera angle, perspective, shot type

# Lighting:
lighting conditions, quality, direction

# Negative Prompt:
things to avoid in the generation
```

---

## 🔧 How to Use Templates

### In Blender:

1. **Enable Prompt Builder**
   - Open Style Engine workspace
   - In the UI panel, enable "Use Prompt Builder" checkbox

2. **Load a Template**
   - In the text editor, click the text icon dropdown
   - Select a template (e.g., `STYLEENGINE_Vizdev`)
   - The template will load with pre-filled tags

3. **Customize the Prompt**
   - Modify any tag content to fit your needs
   - Leave tags empty if not needed
   - Add or remove content as desired

4. **Generate**
   - Press Alt+W → Generate Image
   - The Prompt Builder will parse the tags and create a coherent prompt

---

## ✍️ Creating Custom Templates

To create your own template:

1. **Create a new text file** in this directory
2. **Name it:** `STYLEENGINE_YourName.txt`
   - Must start with `STYLEENGINE_`
   - Use underscores instead of spaces
3. **Use the tag format** shown above
4. **Fill in your default values** for each tag
5. **Reload addon** or restart Blender to see your template

---

## 🎯 Tag Descriptions

| Tag | Purpose | Example |
|-----|---------|---------|
| **Subject** | Main focal point | "futuristic city", "ancient temple" |
| **Style** | Art style and medium | "concept art, matte painting", "8k photography" |
| **Details** | Specific features | "detailed architecture", "crisp textures" |
| **Environment** | Setting/background | "mountain landscape", "studio setup" |
| **Mood** | Atmosphere/feeling | "cinematic, epic", "clean, professional" |
| **Camera** | Perspective/angle | "wide-angle shot", "professional camera" |
| **Lighting** | Light conditions | "dramatic natural light", "studio lighting" |
| **Negative Prompt** | Things to avoid | "blurry, low quality, cartoon" |

---

## 💡 Tips for Effective Prompts

### For Vizdev/Concept Art:
- ✅ Use "concept art", "matte painting", "visual development"
- ✅ Include "painterly", "atmospheric", "cinematic"
- ✅ Specify "establishing shot", "wide-angle"
- ✅ Mention "dramatic lighting", "atmospheric depth"
- ❌ Avoid "photorealistic", "photograph"

### For Photorealistic:
- ✅ Use "photorealistic", "professional photography", "8k"
- ✅ Include "sharp focus", "highly detailed", "crisp"
- ✅ Specify "studio lighting", "proper exposure"
- ✅ Mention "professional camera", "depth of field"
- ❌ Avoid "painting", "illustration", "artistic"

---

## 📌 Template Philosophy

These templates are designed to be:
- **Professional** - Industry-standard terminology
- **Focused** - Clear purpose for each template
- **Flexible** - Easy to customize for your needs
- **Effective** - Optimized keywords for SDXL

**Less is more:** We provide 3 focused templates instead of many random examples. This keeps the workflow clean and purposeful.

---

## 🚀 Advanced Usage

### Mixing Styles:
You can combine elements from different templates:
- Start with Vizdev template
- Add photorealistic lighting keywords
- Adjust negative prompt accordingly

### Iteration:
- Generate with template
- Note what works/doesn't work
- Adjust tags incrementally
- Save successful combinations as new templates

---

## 📝 Notes

- Templates are loaded at addon startup
- Changes to templates require addon reload
- Template names must start with `STYLEENGINE_`
- Use comment-style tags (# Tag Name:), not HTML tags
- Empty tags are ignored by the parser

---

**Ready to create!** Choose a template, customize it, and generate amazing AI images with Style Engine. 🎨✨
