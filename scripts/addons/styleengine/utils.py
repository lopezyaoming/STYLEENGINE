# ================================================================
#    Style Engine Utilities
#    Helper functions for accessing preferences and API credentials
# ================================================================

import bpy
import os
from datetime import datetime


def get_preferences():
    """Get the Style Engine addon preferences."""
    return bpy.context.preferences.addons['styleengine'].preferences


def is_heavypoly_compatible():
    """
    Check if HEAVYPOLY compatibility mode is enabled.
    
    Returns:
        bool: True if HEAVYPOLY integration is enabled
    """
    try:
        prefs = get_preferences()
        return prefs.enable_heavypoly_compatibility
    except:
        return False


def get_runcomfy_api_token():
    """
    Get the RunComfy API token.
    Returns the environment variable if available and preferred, 
    otherwise returns the manually entered value.
    
    Returns:
        str: The API token, or empty string if not set
    """
    prefs = get_preferences()
    
    if prefs.use_env_vars:
        env_token = os.environ.get('RUNCOMFY_API_TOKEN', '')
        if env_token:
            return env_token
    
    return prefs.runcomfy_api_token


def get_runcomfy_user_id():
    """
    Get the RunComfy User ID.
    Returns the environment variable if available and preferred,
    otherwise returns the manually entered value.
    
    Returns:
        str: The User ID, or empty string if not set
    """
    prefs = get_preferences()
    
    if prefs.use_env_vars:
        env_user_id = os.environ.get('RUNCOMFY_USER_ID', '')
        if env_user_id:
            return env_user_id
    
    return prefs.runcomfy_user_id


def validate_runcomfy_credentials():
    """
    Validate that RunComfy credentials are set.
    
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    api_token = get_runcomfy_api_token()
    user_id = get_runcomfy_user_id()
    
    if not api_token:
        return False, "RunComfy API Token is not set. Please configure it in addon preferences."
    
    if not user_id:
        return False, "RunComfy User ID is not set. Please configure it in addon preferences."
    
    return True, "Credentials are valid"


def get_api_headers():
    """
    Get the headers for RunComfy API requests.
    
    Returns:
        dict: Headers dictionary for API requests
    """
    api_token = get_runcomfy_api_token()
    
    return {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }


def parse_credentials_file(file_path=None):
    """
    Parse credentials.txt file and extract RunComfy credentials.
    
    If file_path is provided, uses that path.
    Otherwise, looks for credentials.txt in:
    1. scripts/addons/styleengine/credentials.txt
    2. scripts/addons/credentials.txt
    
    Expected format:
        RUNCOMFY_API_TOKEN: <token>
        RUNCOMFY_USER_ID: <user_id>
        Workflow ID: <workflow_id>
        Deployment ID: <deployment_id>
    
    Args:
        file_path (str, optional): Path to credentials file. If None, searches default locations.
    
    Returns:
        tuple: (success: bool, data: dict, message: str)
               data contains: api_token, user_id, workflow_id, deployment_id
    """
    import os
    from pathlib import Path
    
    credentials_file = None
    
    # If user provided a path, use it
    if file_path and file_path.strip():
        credentials_file = Path(file_path)
        if not credentials_file.exists():
            return (False, {}, f"File not found: {file_path}")
    else:
        # Get addon directory and search default locations
        addon_dir = Path(__file__).parent
        
        # Try multiple locations
        possible_paths = [
            addon_dir / "credentials.txt",                    # styleengine/credentials.txt
            addon_dir.parent / "credentials.txt",             # addons/credentials.txt
        ]
        
        for path in possible_paths:
            if path.exists():
                credentials_file = path
                break
        
        if not credentials_file:
            return (False, {}, "credentials.txt not found. Please specify a file path or create it in the addon directory.")
    
    # Parse the file
    try:
        data = {
            'api_token': None,
            'user_id': None,
            'workflow_id': None,
            'deployment_id': None
        }
        
        with open(credentials_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse key: value format
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Map to our keys
                    if key == 'RUNCOMFY_API_TOKEN':
                        data['api_token'] = value
                    elif key == 'RUNCOMFY_USER_ID':
                        data['user_id'] = value
                    elif key == 'Workflow ID':
                        data['workflow_id'] = value
                    elif key == 'Deployment ID':
                        data['deployment_id'] = value
        
        # Validate we got at least the API token and User ID
        if not data['api_token'] or not data['user_id']:
            return (False, data, "Missing required credentials (RUNCOMFY_API_TOKEN or RUNCOMFY_USER_ID)")
        
        return (True, data, f"Successfully parsed credentials from {credentials_file.name}")
        
    except Exception as e:
        return (False, {}, f"Error reading credentials.txt: {str(e)}")


# ================================================================
#    Text Editor Integration for Prompts
# ================================================================

def get_or_create_prompt_text():
    """
    Get or create the Style Engine prompt text block with default template.
    This allows users to write long, multi-line prompts in Blender's text editor.
    
    Returns:
        bpy.types.Text: The text block for prompt editing
    """
    text_name = "STYLEENGINE_Prompt"
    
    if text_name not in bpy.data.texts:
        # Create new text block
        text = bpy.data.texts.new(text_name)
        
        # Write default template with HTML-style tags
        text.write("# Keywords\n")
        text.write("<k></k>\n")
        text.write("# Prompt\n")
        text.write("<p></p>\n")
        text.write("# Negative Prompt\n")
        text.write("<n>worst quality, low quality, lowres, blurry, jpeg artifacts, pixelated, bad composition, out of focus, noise, watermark, text, logo, signature, cropped, out of frame</n>\n")
        text.write("# Machine Vision\n")
        text.write("<v></v>\n")
        
        print(f"[Style Engine] Created prompt text block: {text_name}")
    else:
        text = bpy.data.texts[text_name]
    
    return text


def get_prompt_from_text_editor():
    """
    Read the prompt from the text editor, filtering out comments and empty lines.
    
    Returns:
        str: The cleaned prompt text, or empty string if not found
    """
    text = bpy.data.texts.get("STYLEENGINE_Prompt")
    
    if not text:
        print("[Style Engine] ⚠️ STYLEENGINE_Prompt text block not found!")
        return ""
    
    # Get raw content
    raw_content = text.as_string()
    print(f"[Style Engine] 📖 Raw text editor content ({len(raw_content)} chars):")
    print(f"[Style Engine]    '{raw_content}'")
    
    lines = []
    for line in raw_content.split('\n'):
        stripped = line.strip()
        # Skip comments (lines starting with #) and empty lines
        if stripped and not stripped.startswith('#'):
            lines.append(stripped)
            print(f"[Style Engine]    ✓ Included line: '{stripped}'")
        elif stripped:
            print(f"[Style Engine]    ✗ Skipped comment: '{stripped}'")
    
    # Join with spaces (cross-platform safe)
    prompt = ' '.join(lines)
    print(f"[Style Engine] 📝 Final prompt after processing: '{prompt}'")
    return prompt


def save_prompt_to_text_editor(prompt_text):
    """
    Save the current prompt to the text editor.
    
    Args:
        prompt_text (str): The prompt text to save
    """
    text = get_or_create_prompt_text()
    
    # Clear existing content
    text.clear()
    
    # Write header
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    text.write("# ===================================\n")
    text.write("# STYLE ENGINE PROMPT EDITOR\n")
    text.write(f"# Last saved: {now}\n")
    text.write("# ===================================\n\n")
    
    # Write the prompt
    text.write(prompt_text)
    text.write("\n")
    
    print(f"[Style Engine] Saved prompt to text editor ({len(prompt_text)} chars)")


def build_reference_workflow(context, base_image_path, prompt):
    """
    Build the SDXLREF workflow JSON with reference images from properties.
    
    Args:
        context: Blender context
        base_image_path: Path to the base image from viewport (AO/depth input)
        prompt: The text prompt for generation
        
    Returns:
        dict: The complete workflow JSON ready to send to ComfyUI
    """
    import json
    import os
    
    # Get addon directory
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_path = os.path.join(os.path.dirname(addon_dir), 'ComfyUI', 'runcomfyWorkflows', 'SDXLREF.json')
    
    # Load the SDXLREF template
    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
    except Exception as e:
        print(f"[Style Engine] ❌ Error loading SDXLREF.json: {e}")
        return None
    
    # Get properties
    props = context.scene.style_engine_props
    
    # ================================================================
    # BASE PARAMETERS
    # ================================================================
    
    # Set base image (node 15: AO input)
    workflow["15"]["inputs"]["image"] = base_image_path
    
    # Set prompt (node 25)
    workflow["25"]["inputs"]["value"] = prompt
    
    # Set steps (node 42)
    workflow["42"]["inputs"]["value"] = props.steps
    
    # Set depth and canny strength (nodes 40, 41)
    workflow["40"]["inputs"]["value"] = props.silhouette_influence  # Canny
    workflow["41"]["inputs"]["value"] = props.depth_influence  # Depth
    
    # ================================================================
    # GLOBAL STRENGTHS
    # ================================================================
    
    # Node 52: StyleTransferStrength
    workflow["52"]["inputs"]["value"] = props.style_transfer_strength
    
    # Node 90: CompositionStrength
    workflow["90"]["inputs"]["value"] = props.composition_strength
    
    # Node 91: ForceTransferStrength
    workflow["91"]["inputs"]["value"] = props.force_transfer_strength
    
    # ================================================================
    # STYLE TRANSFER IMAGES (ST1-ST5)
    # ================================================================
    
    st_mapping = [
        ("st1", "65", "129"),  # (property prefix, image node, weight node)
        ("st2", "63", "126"),
        ("st3", "64", "125"),
        ("st4", "94", "124"),
        ("st5", "97", "123"),
    ]
    
    for prop_prefix, img_node, weight_node in st_mapping:
        img = getattr(props, f"{prop_prefix}_image")
        weight = getattr(props, f"{prop_prefix}_weight")
        
        if img and img.filepath:
            # Set image path
            workflow[img_node]["inputs"]["image"] = os.path.basename(img.filepath)
            # Set weight
            workflow[weight_node]["inputs"]["value"] = weight
        else:
            # No image - set weight to 0
            workflow[weight_node]["inputs"]["value"] = 0.0
    
    # ================================================================
    # COMPOSITION IMAGES (COMP1-COMP5)
    # ================================================================
    
    comp_mapping = [
        ("comp1", "78", "122"),  # (property prefix, image node, weight node)
        ("comp2", "77", "121"),
        ("comp3", "76", "120"),
        ("comp4", "100", "119"),
        ("comp5", "103", "118"),
    ]
    
    for prop_prefix, img_node, weight_node in comp_mapping:
        img = getattr(props, f"{prop_prefix}_image")
        weight = getattr(props, f"{prop_prefix}_weight")
        
        if img and img.filepath:
            # Set image path
            workflow[img_node]["inputs"]["image"] = os.path.basename(img.filepath)
            # Set weight
            workflow[weight_node]["inputs"]["value"] = weight
        else:
            # No image - set weight to 0
            workflow[weight_node]["inputs"]["value"] = 0.0
    
    # ================================================================
    # STRONG STYLE TRANSFER IMAGES (SST1-SST5)
    # ================================================================
    
    sst_mapping = [
        ("sst1", "89", "117"),  # (property prefix, image node, weight node)
        ("sst2", "88", "116"),
        ("sst3", "87", "115"),
        ("sst4", "106", "114"),
        ("sst5", "109", "113"),
    ]
    
    for prop_prefix, img_node, weight_node in sst_mapping:
        img = getattr(props, f"{prop_prefix}_image")
        weight = getattr(props, f"{prop_prefix}_weight")
        
        if img and img.filepath:
            # Set image path
            workflow[img_node]["inputs"]["image"] = os.path.basename(img.filepath)
            # Set weight
            workflow[weight_node]["inputs"]["value"] = weight
        else:
            # No image - set weight to 0
            workflow[weight_node]["inputs"]["value"] = 0.0
    
    print(f"[Style Engine] ✓ Built SDXLREF workflow with reference images")
    print(f"  - Style Transfer Strength: {props.style_transfer_strength}")
    print(f"  - Composition Strength: {props.composition_strength}")
    print(f"  - Force Transfer Strength: {props.force_transfer_strength}")
    
    # Count active images
    active_st = sum(1 for p, _, _ in st_mapping if getattr(props, f"{p}_image"))
    active_comp = sum(1 for p, _, _ in comp_mapping if getattr(props, f"{p}_image"))
    active_sst = sum(1 for p, _, _ in sst_mapping if getattr(props, f"{p}_image"))
    print(f"  - Active images: ST={active_st}, COMP={active_comp}, SST={active_sst}")
    
    return workflow


# ================================================================
#    Prompt Builder - HTML-Style Tag System
# ================================================================

def parse_prompt_tags(text):
    """
    Parse HTML-style tags from text.
    
    Expected format:
        <k>keywords here</k>
        <p>main prompt here</p>
        <n>negative prompt here</n>
    
    Tags:
    - <k></k>: Keywords (optional, prepended to prompt)
    - <p></p>: Main prompt (required)
    - <n></n>: Negative prompt (optional)
    
    Args:
        text (str): Text containing HTML-style tags
    
    Returns:
        dict: {'keywords': str, 'prompt': str, 'negative': str}
    """
    import re
    
    # Default empty values
    parsed = {
        'keywords': '',
        'prompt': '',
        'negative': ''
    }
    
    # Pattern: <tag>content</tag> (case-insensitive, multi-line)
    
    # Extract keywords (<k>...</k>)
    k_match = re.search(r'<k>(.*?)</k>', text, re.DOTALL | re.IGNORECASE)
    if k_match:
        # Clean up: strip whitespace, normalize spaces
        parsed['keywords'] = ' '.join(k_match.group(1).strip().split())
    
    # Extract prompt (<p>...</p>)
    p_match = re.search(r'<p>(.*?)</p>', text, re.DOTALL | re.IGNORECASE)
    if p_match:
        # Clean up: strip whitespace, normalize spaces
        parsed['prompt'] = ' '.join(p_match.group(1).strip().split())
    
    # Extract negative (<n>...</n>)
    n_match = re.search(r'<n>(.*?)</n>', text, re.DOTALL | re.IGNORECASE)
    if n_match:
        # Clean up: strip whitespace, normalize spaces
        parsed['negative'] = ' '.join(n_match.group(1).strip().split())
    
    return parsed


def build_prompt_from_template(parsed_tags):
    """
    Build final prompt from parsed tags.
    
    Logic: Keywords + Prompt = Final Positive Prompt
    
    Args:
        parsed_tags (dict): Dictionary with 'keywords', 'prompt', 'negative'
    
    Returns:
        tuple: (positive_prompt: str, negative_prompt: str)
    """
    keywords = parsed_tags.get('keywords', '').strip()
    prompt = parsed_tags.get('prompt', '').strip()
    negative = parsed_tags.get('negative', '').strip()
    
    # Concatenate keywords + prompt (with comma separator if both exist)
    parts = []
    if keywords:
        parts.append(keywords)
    if prompt:
        parts.append(prompt)
    
    # Join with comma + space
    final_prompt = ', '.join(parts) if parts else ''
    
    return (final_prompt, negative)


def process_prompt_builder(text):
    """
    Main entry point for prompt builder.
    Parses HTML-style tags and builds prompt.
    
    Args:
        text (str): Raw text from text editor (with HTML tags)
    
    Returns:
        tuple: (positive_prompt: str, negative_prompt: str)
               If parsing fails, returns (text, "")
    """
    if not text or not text.strip():
        return ("", "")
    
    # Check if text contains HTML-style tags
    text_lower = text.lower()
    has_tags = ('<k>' in text_lower or '<p>' in text_lower or '<n>' in text_lower)
    
    if not has_tags:
        # No tags found, return as-is (fallback to raw text)
        return (text.strip(), "")
    
    # Parse tags
    parsed = parse_prompt_tags(text)
    
    # Check if we parsed anything meaningful
    if not parsed['keywords'] and not parsed['prompt']:
        # No content in tags, return original text
        return (text.strip(), "")
    
    # Build prompt
    positive, negative = build_prompt_from_template(parsed)
    
    return (positive, negative)


# ================================================================
#    Template Management
# ================================================================

def get_templates_directory():
    """
    Get the path to the templates directory.
    
    Returns:
        Path: Path object pointing to templates folder
    """
    from pathlib import Path
    addon_dir = Path(__file__).parent
    templates_dir = addon_dir / "templates"
    
    # Create if doesn't exist
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Style Engine] Created templates directory: {templates_dir}")
    
    return templates_dir


def list_templates():
    """
    List all available prompt templates.
    
    Returns:
        list: List of template filenames (without path)
    """
    templates_dir = get_templates_directory()
    
    # Find all .txt and .md files starting with STYLEENGINE_
    templates = []
    for ext in ['.txt', '.md']:
        pattern = f"STYLEENGINE_*{ext}"
        for template_file in templates_dir.glob(pattern):
            templates.append(template_file.name)
    
    # Debug: Show what was found
    if templates:
        print(f"[Style Engine] Found {len(templates)} template(s) in {templates_dir}")
    else:
        print(f"[Style Engine] No templates found in {templates_dir}")
        print(f"[Style Engine] Templates folder exists: {templates_dir.exists()}")
        if templates_dir.exists():
            all_files = list(templates_dir.glob("*"))
            print(f"[Style Engine] Files in folder: {[f.name for f in all_files]}")
    
    return sorted(templates)


def load_template_to_text_editor(template_name):
    """
    Load a template file into Blender's text editor.
    
    Creates a new text block with the template's content.
    
    Args:
        template_name (str): Name of template file (with or without extension)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    import bpy
    from pathlib import Path
    
    templates_dir = get_templates_directory()
    
    # Handle both "STYLEENGINE_Template" and "STYLEENGINE_Template.txt"
    if not template_name.endswith(('.txt', '.md')):
        # Try to find the file with .txt extension first
        template_path = templates_dir / f"{template_name}.txt"
        if not template_path.exists():
            template_path = templates_dir / f"{template_name}.md"
    else:
        template_path = templates_dir / template_name
    
    if not template_path.exists():
        return (False, f"Template not found: {template_name}")
    
    try:
        # Read template content
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get text block name (remove extension)
        text_name = template_path.stem
        
        # Check if text block already exists
        if text_name in bpy.data.texts:
            text_block = bpy.data.texts[text_name]
            text_block.clear()
            text_block.write(content)
            action = "Updated"
        else:
            text_block = bpy.data.texts.new(text_name)
            text_block.write(content)
            action = "Created"
        
        return (True, f"{action} text block: {text_name}")
    
    except Exception as e:
        return (False, f"Error loading template: {e}")


def load_all_templates():
    """
    Load all templates from the templates folder into Blender's text editor.
    
    Returns:
        tuple: (count: int, message: str)
    """
    templates = list_templates()
    
    if not templates:
        return (0, "No templates found in templates folder")
    
    loaded_count = 0
    errors = []
    
    for template in templates:
        success, message = load_template_to_text_editor(template)
        if success:
            loaded_count += 1
            print(f"[Style Engine] {message}")
        else:
            errors.append(message)
    
    if errors:
        error_msg = "; ".join(errors)
        return (loaded_count, f"Loaded {loaded_count} templates ({len(errors)} errors: {error_msg})")
    
    return (loaded_count, f"Loaded {loaded_count} template(s)")


def save_current_prompt_as_template(template_name):
    """
    Save the currently active text editor content as a template file.
    
    Tries to get the active text from any open text editor area first,
    then falls back to STYLEENGINE_Prompt if no text editor is active.
    
    Args:
        template_name (str): Name for the new template (will be prefixed with STYLEENGINE_)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    import bpy
    from pathlib import Path
    
    # Try to get the currently active text from any text editor area
    active_text = None
    source_name = None
    
    for area in bpy.context.screen.areas:
        if area.type == 'TEXT_EDITOR':
            for space in area.spaces:
                if space.type == 'TEXT_EDITOR' and space.text:
                    active_text = space.text
                    source_name = space.text.name
                    break
            if active_text:
                break
    
    # Fallback to STYLEENGINE_Prompt if no text editor is active
    if not active_text:
        active_text = bpy.data.texts.get('STYLEENGINE_Prompt')
        source_name = 'STYLEENGINE_Prompt'
        if not active_text:
            return (False, "No active text editor found and STYLEENGINE_Prompt doesn't exist")
    
    content = active_text.as_string()
    if not content.strip():
        return (False, f"Cannot save empty template (from {source_name})")
    
    # Ensure name starts with STYLEENGINE_
    if not template_name.startswith('STYLEENGINE_'):
        template_name = f"STYLEENGINE_{template_name}"
    
    # Ensure .txt extension
    if not template_name.endswith('.txt'):
        template_name = f"{template_name}.txt"
    
    # Get templates directory
    templates_dir = get_templates_directory()
    template_path = templates_dir / template_name
    
    try:
        # Save to file
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return (True, f"Saved template: {template_name} (from {source_name})")
    
    except Exception as e:
        return (False, f"Error saving template: {e}")


