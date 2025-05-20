#!/usr/bin/env python3
"""
Utility functions for the Field Museum Bedrock Transcription application.
Includes functions for file operations, JSON handling, and prompt conversions.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Union, Optional

def striplines(text):
    return [s.strip() for s in text.splitlines()]
    
def get_blank_transcript(prompt_text):
    fieldnames = get_fieldnames_from_prompt_text(prompt_text)
    return {fieldname: "" for fieldname in fieldnames}

def get_fieldnames_from_prompt_text(prompt_text):
    prompt_text = "\n".join(striplines(prompt_text))
    fieldnames = re.findall(r"(^\w+):", prompt_text, flags=re.MULTILINE)
    return fieldnames 

def get_content(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        return f.read()       

def ensure_directory_exists(directory: str) -> None:
    """
    Create a directory if it doesn't exist.
    
    Args:
        directory: Path to the directory to create
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_json(file_path: str) -> Any:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        The loaded JSON data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {str(e)}")
        raise

def save_json(data: Any, file_path: str, indent: int = 2) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: The data to save
        file_path: Path to the JSON file
        indent: Number of spaces for indentation (default: 2)
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving JSON to {file_path}: {str(e)}")
        raise

def read_text_file(file_path: str) -> str:
    """
    Read text from a file.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        The file contents as a string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        raise
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        raise

def write_text_file(text: str, file_path: str) -> None:
    """
    Write text to a file.
    
    Args:
        text: The text to write
        file_path: Path to the text file
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception as e:
        print(f"Error writing to file {file_path}: {str(e)}")
        raise

def append_text_file(text: str, file_path: str) -> None:
    """
    Append text to a file.
    
    Args:
        text: The text to append
        file_path: Path to the text file
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(text)
    except Exception as e:
        print(f"Error appending to file {file_path}: {str(e)}")
        raise

def prompt_to_json(prompt_text: str) -> Dict[str, Any]:
    """
    Convert a text prompt to a structured JSON format.
    
    This function parses a text prompt that contains field descriptions
    and converts it to a JSON structure with field names and descriptions.
    
    Args:
        prompt_text: The text prompt to convert
        
    Returns:
        A dictionary with the parsed prompt structure
    """
    # Initialize the result dictionary
    result = {
        "title": "",
        "description": "",
        "fields": []
    }
    
    # Extract the title and description (everything before the first field)
    lines = prompt_text.strip().split('\n')
    description_lines = []
    
    # Find where the fields start
    field_start_idx = 0
    for i, line in enumerate(lines):
        if re.search(r'^\s*\w+\s*:', line):
            field_start_idx = i
            break
        description_lines.append(line)
    
    # Set the title and description
    if description_lines:
        result["title"] = description_lines[0].strip()
        if len(description_lines) > 1:
            result["description"] = '\n'.join(description_lines[1:]).strip()
    
    # Process fields
    current_field = None
    current_description = []
    
    for i in range(field_start_idx, len(lines)):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Check if this line starts a new field
        field_match = re.match(r'^(\w+)\s*:\s*(.*)', line)
        if field_match:
            # Save the previous field if it exists
            if current_field:
                result["fields"].append({
                    "name": current_field,
                    "description": '\n'.join(current_description).strip()
                })
            
            # Start a new field
            current_field = field_match.group(1)
            current_description = [field_match.group(2)]
        else:
            # Continue with the current field description
            if current_field:
                current_description.append(line)
    
    # Add the last field
    if current_field:
        result["fields"].append({
            "name": current_field,
            "description": '\n'.join(current_description).strip()
        })
    
    return result

def json_to_prompt(prompt_json: Dict[str, Any]) -> str:
    """
    Convert a JSON prompt structure back to text format.
    
    Args:
        prompt_json: The JSON structure to convert
        
    Returns:
        A formatted text prompt
    """
    lines = []
    
    # Add title and description
    if "title" in prompt_json and prompt_json["title"]:
        lines.append(prompt_json["title"])
        lines.append("")
    
    if "description" in prompt_json and prompt_json["description"]:
        lines.append(prompt_json["description"])
        lines.append("")
    
    # Add fields
    if "fields" in prompt_json:
        for field in prompt_json["fields"]:
            if "name" in field and "description" in field:
                lines.append(f"{field['name']}: {field['description']}")
                lines.append("")
    
    return '\n'.join(lines)

def json_to_string(data: Any, indent: int = 2) -> str:
    """
    Convert any JSON-serializable data to a formatted string.
    
    Args:
        data: The data to convert
        indent: Number of spaces for indentation (default: 2)
        
    Returns:
        A formatted JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)

def string_to_json(json_string: str) -> Any:
    """
    Convert a JSON string to a Python object.
    
    Args:
        json_string: The JSON string to convert
        
    Returns:
        The parsed JSON data
        
    Raises:
        json.JSONDecodeError: If the string contains invalid JSON
    """
    return json.loads(json_string)

def get_prompt_fields(prompt_text: str) -> List[str]:
    """
    Extract field names from a text prompt.
    
    Args:
        prompt_text: The text prompt to analyze
        
    Returns:
        A list of field names found in the prompt
    """
    fields = []
    for line in prompt_text.split('\n'):
        field_match = re.match(r'^(\w+)\s*:', line)
        if field_match:
            fields.append(field_match.group(1))
    return fields

def create_prompt_template(title: str, description: str, fields: List[Dict[str, str]]) -> str:
    """
    Create a prompt template from components.
    
    Args:
        title: The prompt title
        description: The prompt description
        fields: A list of dictionaries with 'name' and 'description' keys
        
    Returns:
        A formatted prompt template
    """
    lines = [title, "", description, ""]
    
    for field in fields:
        lines.append(f"{field['name']}: {field['description']}")
        lines.append("")
    
    return '\n'.join(lines)

def save_prompt_as_json(prompt_text: str, output_path: str) -> None:
    """
    Convert a text prompt to JSON and save it to a file.
    
    Args:
        prompt_text: The text prompt to convert
        output_path: Path to save the JSON file
    """
    prompt_json = prompt_to_json(prompt_text)
    save_json(prompt_json, output_path)

def load_prompt_from_json(json_path: str) -> str:
    """
    Load a JSON prompt file and convert it to text format.
    
    Args:
        json_path: Path to the JSON prompt file
        
    Returns:
        The prompt in text format
    """
    prompt_json = load_json(json_path)
    return json_to_prompt(prompt_json)

def batch_convert_prompts(input_dir: str, output_dir: str, to_json: bool = True) -> None:
    """
    Batch convert prompts between text and JSON formats.
    
    Args:
        input_dir: Directory containing input files
        output_dir: Directory to save output files
        to_json: If True, convert text to JSON; if False, convert JSON to text
    """
    # Ensure output directory exists
    ensure_directory_exists(output_dir)
    
    # Get all files in the input directory
    input_path = Path(input_dir)
    
    if to_json:
        # Convert text files to JSON
        for file_path in input_path.glob('*.txt'):
            prompt_text = read_text_file(str(file_path))
            output_file = Path(output_dir) / f"{file_path.stem}.json"
            save_prompt_as_json(prompt_text, str(output_file))
            print(f"Converted {file_path} to {output_file}")
    else:
        # Convert JSON files to text
        for file_path in input_path.glob('*.json'):
            output_file = Path(output_dir) / f"{file_path.stem}.txt"
            prompt_text = load_prompt_from_json(str(file_path))
            write_text_file(prompt_text, str(output_file))
            print(f"Converted {file_path} to {output_file}")

if __name__ == "__main__":
    # Example usage
    print("Utility functions for Field Museum Bedrock Transcription")
    print("Import this module to use the functions in your application.")