#!/usr/bin/env python3
"""
Base64 filter for Field Museum Bedrock Transcription application.
This module provides utilities for detecting and filtering base64 content.
"""

import re
import json
from typing import Any, Dict, Union, List

# Regular expression to detect likely base64 content
BASE64_PATTERN = re.compile(r'[A-Za-z0-9+/]{50,}={0,2}')

def is_likely_base64(text: str) -> bool:
    """
    Check if a string is likely to be base64 encoded data.
    
    Args:
        text: The string to check
        
    Returns:
        True if the string is likely base64 encoded, False otherwise
    """
    # Check if the string matches the base64 pattern
    if BASE64_PATTERN.search(text):
        # Additional check: base64 strings should have a length that's a multiple of 4
        # (or padded with = to make it so)
        if len(text) % 4 == 0 or text.endswith('=') or text.endswith('=='):
            return True
    return False

def filter_base64(text: str) -> str:
    """
    Filter out base64 content from a string.
    
    Args:
        text: The string to filter
        
    Returns:
        The filtered string with base64 content replaced
    """
    def replace_base64(match):
        base64_str = match.group(0)
        return f"[BASE64 DATA (length: {len(base64_str)})]"
    
    return BASE64_PATTERN.sub(replace_base64, text)

def filter_base64_from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively filter base64 content from a dictionary.
    
    Args:
        data: The dictionary to filter
        
    Returns:
        A new dictionary with base64 content filtered
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            if is_likely_base64(value):
                result[key] = f"[BASE64 DATA (length: {len(value)})]"
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = filter_base64_from_dict(value)
        elif isinstance(value, list):
            result[key] = filter_base64_from_list(value)
        else:
            result[key] = value
    
    return result

def filter_base64_from_list(data: List[Any]) -> List[Any]:
    """
    Recursively filter base64 content from a list.
    
    Args:
        data: The list to filter
        
    Returns:
        A new list with base64 content filtered
    """
    if not isinstance(data, list):
        return data
    
    result = []
    for item in data:
        if isinstance(item, str):
            if is_likely_base64(item):
                result.append(f"[BASE64 DATA (length: {len(item)})]")
            else:
                result.append(item)
        elif isinstance(item, dict):
            result.append(filter_base64_from_dict(item))
        elif isinstance(item, list):
            result.append(filter_base64_from_list(item))
        else:
            result.append(item)
    
    return result

def filter_base64_from_json(json_str: str) -> str:
    """
    Filter base64 content from a JSON string.
    
    Args:
        json_str: The JSON string to filter
        
    Returns:
        A new JSON string with base64 content filtered
    """
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            filtered_data = filter_base64_from_dict(data)
        elif isinstance(data, list):
            filtered_data = filter_base64_from_list(data)
        else:
            return json_str
        
        return json.dumps(filtered_data, indent=2)
    except json.JSONDecodeError:
        # If it's not valid JSON, just filter the string directly
        return filter_base64(json_str)

# Example usage
if __name__ == "__main__":
    # Test with a string containing base64
    test_str = "This is a test with base64: ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
    filtered_str = filter_base64(test_str)
    print(f"Original: {test_str}")
    print(f"Filtered: {filtered_str}")
    
    # Test with a dictionary containing base64
    test_dict = {
        "name": "Test",
        "image": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",
        "nested": {
            "image2": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        }
    }
    filtered_dict = filter_base64_from_dict(test_dict)
    print(f"\nOriginal dict: {test_dict}")
    print(f"Filtered dict: {filtered_dict}")
    
    # Test with a JSON string containing base64
    test_json = '{"name": "Test", "image": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="}'
    filtered_json = filter_base64_from_json(test_json)
    print(f"\nOriginal JSON: {test_json}")
    print(f"Filtered JSON: {filtered_json}")