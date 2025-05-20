#!/usr/bin/env python3
"""
Test Nova models with the fixed format for image processing capabilities.
"""

from model_tester import ModelTester
import json
import boto3
import base64
import time
from typing import Dict, Any, List
from pathlib import Path

def load_image_to_base64(image_path: str) -> str:
    """Load an image file and convert it to base64."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error loading image: {str(e)}")
        return ""

def load_prompt_text(prompt_file: str) -> str:
    """Load prompt text from a file."""
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading prompt file: {e}")
        return ""

def test_nova_model_directly(model_id: str, base64_image: str, prompt_text: str) -> Dict[str, Any]:
    """Test a Nova model directly with the correct format."""
    print(f"\nTesting Nova model {model_id} directly")
    
    bedrock_client = boto3.client("bedrock-runtime")
    
    # Format for Nova models
    request_body = {
        "schemaVersion": "messages-v1",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": "jpeg",
                        "source": {"bytes": base64_image},
                    }
                },
                {
                    "text": "Transcribe all text in this image."
                }
            ],
        }],
        "system": [{
            "text": prompt_text
        }],
        "inferenceConfig": {"max_new_tokens": 4096, "top_p": 0.9, "temperature": 0.7}
    }
    
    try:
        # Invoke the model
        start_time = time.time()
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        elapsed_time = time.time() - start_time
        
        # Parse the response
        response_body = json.loads(response.get("body").read())
        
        # Extract text from response
        text = ""
        if "output" in response_body:
            content = response_body.get("output", {}).get("message", {}).get("content", [])
            for item in content:
                if "text" in item:
                    text = item.get("text", "")
        
        # Get token usage
        usage = response_body.get("usage", {})
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        
        print(f"Success - {elapsed_time:.2f} seconds, {input_tokens} input tokens, {output_tokens} output tokens")
        print(f"Response text (truncated): {text[:200]}...")
        
        return {
            "success": True,
            "elapsed_time": elapsed_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "text": text
        }
    except Exception as e:
        print(f"Error invoking model: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Test Nova models with the fixed format."""
    # Load test image
    base64_image = load_image_to_base64("test_images/Test_Image.jpg")
    if not base64_image:
        print("Failed to load test image.")
        return
    
    # Load prompt text
    prompt_text = load_prompt_text("prompts/1.5Stripped.txt")
    if not prompt_text:
        print("Failed to load prompt text.")
        return
    
    # Test Nova models directly
    nova_models = [
        "amazon.nova-pro-v1:0",
        "amazon.nova-lite-v1:0"
    ]
    
    for model_id in nova_models:
        result = test_nova_model_directly(model_id, base64_image, prompt_text)
        
        if result.get("success"):
            print(f"Model {model_id} processed the image successfully!")
        else:
            print(f"Model {model_id} failed to process the image.")
    
    # Now test using the updated model_tester.py
    print("\nTesting with updated model_tester.py:")
    tester = ModelTester()
    
    # Load all models
    all_models = tester.load_models()
    
    # Filter for Nova models
    nova_models = [m for m in all_models if "nova" in m.get('modelId', '').lower() 
                  and m.get('modelId') in ["amazon.nova-pro-v1:0", "amazon.nova-lite-v1:0"]]
    
    if not nova_models:
        print("No Nova models found.")
        return
    
    print(f"Found {len(nova_models)} Nova models.")
    
    # Test the models
    results = tester.test_models(nova_models)
    
    # Update vision_model_info.json with test results
    tester.update_model_info(results)
    
    # Print summary
    tester.print_summary(results)

if __name__ == "__main__":
    main()