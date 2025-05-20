from bedrock_interface import (
    BedrockImageProcessor,
    ClaudeImageProcessor,
    NovaImageProcessor,
    AmazonImageProcessor,
    MetaImageProcessor,
    MistralImageProcessor,
    create_image_processor
)
import json
from typing import Dict, Any, Optional

def get_vision_models() -> Dict[str, Any]:
    """Get the list of models that support vision capabilities."""
    try:
        # Try to load from model_info directory first
        try:
            with open("model_info/vision_model_info.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # Fall back to root directory
            with open("vision_model_info.json", "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading vision models: {str(e)}")
        return []

def get_best_vision_model() -> Optional[Dict[str, Any]]:
    """Get the best vision model based on test results."""
    models = get_vision_models()
    
    if not models:
        return None
    
    # Sort by success, then by output tokens (higher is better), then by elapsed time (lower is better)
    sorted_models = sorted(
        models,
        key=lambda m: (
            m.get("image_test_success", False),
            m.get("last_test_details", {}).get("output_tokens", 0),
            -m.get("last_test_details", {}).get("elapsed_seconds", float("inf"))
        ),
        reverse=True
    )
    
    return sorted_models[0] if sorted_models else None

def create_best_vision_processor(prompt_name: str, prompt_text: str) -> Optional[BedrockImageProcessor]:
    """Create an image processor using the best available vision model."""
    best_model = get_best_vision_model()
    
    if not best_model:
        return None
    
    model_id = best_model.get("modelId")
    model_name = best_model.get("modelName")
    
    if not model_id or not model_name:
        return None
    
    return create_image_processor("", prompt_name, prompt_text, model_id, model_name)