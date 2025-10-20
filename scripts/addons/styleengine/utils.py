# ================================================================
#    Style Engine Utilities
#    Helper functions for accessing preferences and API credentials
# ================================================================

import bpy
import os


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


