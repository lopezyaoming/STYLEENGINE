# Prompt Templates

This folder contains reusable prompt templates for the **Prompt Builder** feature.

## How to Use

1. **Enable Prompt Builder** - Check the "Enable Prompt Builder" checkbox in the UI
2. **Templates Auto-Load** - All templates in this folder are automatically loaded into Blender's text editor
3. **Use Templates** - Open any STYLEENGINE_* text block, view/modify the content
4. **Generate** - Content is automatically parsed when you generate

## Included Templates

- **STYLEENGINE_Cinematic_Scene.txt** - Futuristic city, concept art style
- **STYLEENGINE_Fantasy_Dragon.txt** - Epic dragon scene, digital painting
- **STYLEENGINE_Portrait_Photo.txt** - Professional portrait photography
- **STYLEENGINE_SciFi_Robot.txt** - Photorealistic 3D robot render
- **STYLEENGINE_Product_Shot.txt** - Commercial product photography

## Creating Your Own Templates

### Method 1: Save from UI
1. Write your prompt in any text block using the tag format (see below)
2. Click **"Save as Template"** button
3. Enter a name (will be prefixed with STYLEENGINE_)
4. Template is saved to this folder

### Method 2: Create File Manually
1. Create a new .txt file in this folder
2. Name it **STYLEENGINE_YourName.txt** (must start with STYLEENGINE_)
3. Write your prompt using the tag format (see below)
4. Click **"Load Templates"** button in UI to refresh

## Template Format

Templates use clean comment-style tags with syntax highlighting:

```python
# Subject:
main subject or focal point

# Style:
art style and medium

# Details:
specific details or actions

# Environment:
background setting or scene context

# Mood:
mood or atmosphere descriptors

# Camera:
camera angle/perspective or lens info

# Lighting:
lighting conditions or color tone

# Negative Prompt:
things to avoid in generation
```

**Note:** In Blender's text editor, the `#` headers will be syntax highlighted, making your templates easy to read!

## Supported File Types

- **.txt** - Plain text (recommended)
- **.md** - Markdown (works too!)

Files must start with **STYLEENGINE_** to be recognized as templates.

## Tips

- **Organize by project** - Create templates for each project/scene
- **Share with team** - Commit this folder to version control
- **Backup custom templates** - Keep copies of your favorites
- **Mix and match** - Combine elements from different templates
- **Use spacing freely** - Empty lines between sections are fine
- **Syntax highlighting** - Tags are highlighted automatically in text editor

## Example Template

```python
# Subject:
cyberpunk street market

# Style:
digital painting, neon aesthetic, blade runner inspired

# Details:
holographic signs, street vendors, rain-slicked pavement

# Environment:
dense urban alley, towering buildings

# Mood:
atmospheric, moody, dystopian

# Camera:
street-level perspective, cinematic framing

# Lighting:
neon lights reflecting in puddles, volumetric fog

# Negative Prompt:
bright daylight, clean, utopian
```

---

**Happy prompting!** 🎨
