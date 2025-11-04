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
        
        # Add header with instructions
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        text.write("# ===================================\n")
        text.write("# STYLE ENGINE PROMPT EDITOR\n")
        text.write(f"# Created: {now}\n")
        text.write("# ===================================\n")
        text.write("#\n")
        text.write("# Lines starting with # are comments (ignored)\n")
        text.write("# Empty lines are also ignored\n")
        text.write("# All other lines become your prompt\n")
        text.write("#\n")
        text.write("# Click 'Sync from Editor' to load into generator\n")
        text.write("# ===================================\n\n")
        
        # Add default prompt
        text.write("This is scene 1. Gotham, Hamster, Dark\n")
        
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
        return ""
    
    lines = []
    for line in text.as_string().split('\n'):
        stripped = line.strip()
        # Skip comments (lines starting with #) and empty lines
        if stripped and not stripped.startswith('#'):
            lines.append(stripped)
    
    # Join with spaces (cross-platform safe)
    prompt = ' '.join(lines)
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


