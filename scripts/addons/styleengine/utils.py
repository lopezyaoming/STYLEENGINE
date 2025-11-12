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


# ================================================================
#    Text Editor Integration for Prompts
# ================================================================

def get_or_create_prompt_text():
    """
    Get or create the Style Engine prompt text block.
    This allows users to write long, multi-line prompts in Blender's text editor.
    
    Returns:
        bpy.types.Text: The text block for prompt editing
    """
    text_name = "STYLEENGINE_Prompt"
    
    if text_name not in bpy.data.texts:
        # Create new text block
        text = bpy.data.texts.new(text_name)
        
        # Start with blank prompt - user writes their own
        # Prompt auto-syncs on generation
        
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


