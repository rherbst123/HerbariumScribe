#!/usr/bin/env python3
"""
Model Tester for Field Museum Bedrock Transcription application.
This module handles testing models for image processing capabilities.
"""

import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import json
import base64
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import traceback
import sys
import os

# Import directly from the current directory
from bedrock_interface_copy import create_image_processor

# Simple error message class to avoid dependency
class ErrorMessage:
    @staticmethod
    def from_exception(e):
        return str(e)

# Simple base64 filter function to avoid dependency
def filter_base64(text):
    if not text:
        return text
    # Simple implementation to filter out base64-like content
    import re
    return re.sub(r'[a-zA-Z0-9+/]{50,}={0,2}', '[BASE64_CONTENT_REMOVED]', text)

def filter_base64_from_dict(data):
    if isinstance(data, dict):
        return {k: filter_base64(v) if isinstance(v, str) else v for k, v in data.items()}
    return data

class ModelTester:
    """Tests AWS Bedrock models for image processing capabilities."""
    
    def __init__(self, prompt_file: str = "prompts/1.5Stripped.txt", test_image: str = "test_images/Test_Image.jpg"):
        """Initialize the ModelTester."""
        self.prompt_text = self.load_prompt_text(prompt_file)
        print(f"{self.prompt_text = }")
        self.base64_image = self.image_to_base64(test_image)
        self.output_dir = Path("test_results")
        self.output_dir.mkdir(exist_ok=True)
    
    def load_prompt_text(self, prompt_file: str) -> str:
        """Load prompt text from a file."""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading prompt file: {e}")
            return ""
    
    def image_to_base64(self, image_path: str) -> str:
        """Convert an image file to base64 encoding."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return ""
    
    def load_models(self, models_file: str = "vision_model_info.json") -> List[Dict[str, Any]]:
        """Load model information from a JSON file."""
        try:
            # Try to load from model_info directory first
            try:
                # llm_processing\bedrock\model_info\vision_model_info.json
                with open(f"llm_processing/bedrock/model_info/{models_file}", 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
                print("backup plan")
                # Fall back to root directory
                with open(models_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading models from {models_file}: {e}")
            return []
    
    def test_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single model for image processing capabilities."""
        model_id = model.get("modelId")
        model_name = model.get("modelName")
        provider = model.get("provider")
        
        # Skip Mistral models
        if model_id.startswith("mistral."):
            print(f"\nSkipping Mistral model: {model_id} ({model_name}) to prevent terminal flooding")
            return {
                "model_id": model_id,
                "provider": provider,
                "model_name": model_name,
                "test_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_seconds": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "input_cost": 0,
                "output_cost": 0,
                "total_cost": 0,
                "response_length": 0,
                "response_text": "Skipped Mistral model to prevent terminal flooding",
                "image_test_success": False,
                "error": "Skipped testing"
            }
        
        print(f"\nTesting model: {model_id} ({model_name})")
        
        result = {
            "model_id": model_id,
            "provider": provider,
            "model_name": model_name,
            "test_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Create processor for this model
            print("creating image processor")
            processor = create_image_processor(
                api_key="",  # Empty as we're using AWS credentials from environment
                prompt_name="transcription_test",
                prompt_text=self.prompt_text,
                model=model_id,
                modelname=model_name
            )
            print("image processor created")
            # Process the image
            start_time = time.time()
            text, processing_data = processor.process_image(self.base64_image, "Test_Image", 0)
            elapsed_time = time.time() - start_time
            
            # Check if the test was successful
            has_error = "error" in processing_data
            no_tokens = processing_data.get("input tokens", 0) == 0 and processing_data.get("output tokens", 0) == 0
            is_successful = not has_error and not no_tokens
            
            # Filter out any base64 content from the response
            filtered_text = filter_base64(text)
            
            # Truncate response text if it's too long
            max_response_length = 1000
            if len(filtered_text) > max_response_length:
                display_text = filtered_text[:max_response_length] + "... [truncated]"
            else:
                display_text = filtered_text
            
            # Store results
            result.update({
                "elapsed_seconds": elapsed_time,
                "input_tokens": processing_data.get("input tokens", 0),
                "output_tokens": processing_data.get("output tokens", 0),
                "input_cost": processing_data.get("input cost $", 0),
                "output_cost": processing_data.get("output cost $", 0),
                "total_cost": (processing_data.get("input cost $", 0) + processing_data.get("output cost $", 0)),
                "response_length": len(text),
                "response_text": display_text,  # Use filtered and truncated text
                "image_test_success": is_successful,
                "error": ""
            })
            
            # Save full response to a separate file
            model_name_safe = model_name.replace(" ", "_").replace(":", "_")
            response_file = self.output_dir / f"{model_name_safe}_response.txt"
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(filtered_text)  # Save filtered text
            
            print(f"  {'Success' if is_successful else 'Failed'} - {elapsed_time:.2f} seconds, {result['input_tokens']} input tokens, {result['output_tokens']} output tokens")
            
        except Exception as e:
            # Use ErrorMessage to handle long error messages
            error_msg = ErrorMessage.from_exception(e)
            
            # Filter out any base64 content from the error message
            filtered_error = filter_base64(str(error_msg))
            
            print(f"  Error testing {model_id}: {filtered_error[:200]}")
            result.update({
                "elapsed_seconds": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "input_cost": 0,
                "output_cost": 0,
                "total_cost": 0,
                "response_length": 0,
                "response_text": f"Error: {filtered_error[:100]}",
                "image_test_success": False,
                "error": filtered_error[:500]  # Use filtered error message
            })
        
        # Flush stdout to ensure output is displayed immediately
        sys.stdout.flush()
        
        return result
    
    def test_models(self, models: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Test multiple models for image processing capabilities."""
        if models is None:
            models = self.load_models()
        
        if not models:
            print("No models to test.")
            return []
        
        # Filter out Mistral models to prevent terminal flooding
        filtered_models = [model for model in models if not model.get("modelId", "").startswith("mistral.")]
        if len(filtered_models) < len(models):
            print(f"Skipping {len(models) - len(filtered_models)} Mistral models to prevent terminal flooding.")
        
        print(f"Testing {len(filtered_models)} models for image processing capabilities...")
        
        results = []
        for model in filtered_models:
            result = self.test_model(model)
            results.append(result)
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]], output_file: Optional[str] = None) -> str:
        """Save test results to JSON file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(self.output_dir / f"model_test_results_{timestamp}.json")
        
        # Create a copy of results with truncated response_text for saving
        results_for_saving = []
        for result in results:
            result_copy = result.copy()
            if "response_text" in result_copy and len(result_copy["response_text"]) > 1000:
                result_copy["response_text"] = result_copy["response_text"][:1000] + "... [truncated]"
            if "error" in result_copy and len(result_copy["error"]) > 500:
                result_copy["error"] = result_copy["error"][:500] + "... [truncated]"
            results_for_saving.append(result_copy)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_for_saving, f, indent=2)
        
        print(f"Results saved to {output_file}")
        return output_file
    
    def update_model_info(self, results: List[Dict[str, Any]], 
                         input_file: str = "vision_model_info.json", 
                         output_file: str = "vision_model_info.json") -> None:
        """Update model information with test results."""
        # Add a note about Mistral models
        for result in results:
            if result.get("model_id", "").startswith("mistral."):
                result["note"] = "Mistral models are currently disabled to prevent terminal flooding"
        
        try:
            # Try to load from model_info directory first
            try:
                input_path = f"llm_processing/bedrock/model_info/{input_file}"
                with open(input_path, 'r') as f:
                    models = json.load(f)
                # If successful, update output path to use model_info directory
                output_file = f"llm_processing/bedrock/model_info/{output_file}"
            except FileNotFoundError:
                # Fall back to root directory
                with open(input_file, 'r') as f:
                    models = json.load(f)
            
            # Create a dictionary of test results by model_id
            test_results = {result["model_id"]: result for result in results}
            
            # Update each model with test results
            for i, model in enumerate(models):
                model_id = model.get("modelId")
                if model_id in test_results:
                    result = test_results[model_id]
                    models[i]["image_test_success"] = result.get("image_test_success", False)
                    models[i]["last_test_timestamp"] = result.get("test_timestamp", "")
                    models[i]["last_test_details"] = {
                        "elapsed_seconds": result.get("elapsed_seconds", 0),
                        "input_tokens": result.get("input_tokens", 0),
                        "output_tokens": result.get("output_tokens", 0),
                        "total_cost": result.get("total_cost", 0),
                        "error": result.get("error", "")[:200] if result.get("error") else ""
                    }
            
            # Save the updated model info
            # Make sure we're using the correct output path
            if output_file.startswith("llm_processing/bedrock/model_info/"):
                # Already using model_info directory
                with open(output_file, 'w') as f:
                    json.dump(models, f, indent=2)
            else:
                # Ensure we save to model_info directory
                os.makedirs("llm_processing/bedrock/model_info", exist_ok=True)
                model_info_path = os.path.join("llm_processing/bedrock/model_info", output_file)
                with open(model_info_path, 'w') as f:
                    json.dump(models, f, indent=2)
                output_file = model_info_path
            
            print(f"Updated {output_file} with test results")
        except Exception as e:
            error_msg = ErrorMessage.from_exception(e)
            print(f"Error updating model info: {error_msg}")
    
    def print_summary(self, results: List[Dict[str, Any]]) -> None:
        """Print a summary of test results."""
        print("\nTest completed. Summary:")
        print(f"Models tested: {len(results)}")
        
        successful = [r for r in results if r.get("image_test_success", False)]
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(results) - len(successful)}")
        
        if successful:
            fastest = min(successful, key=lambda x: x.get("elapsed_seconds", float("inf")))
            cheapest = min(successful, key=lambda x: x.get("total_cost", float("inf")))
            
            print(f"\nFastest model: {fastest['model_id']} ({fastest.get('elapsed_seconds', 0):.2f} seconds)")
            print(f"Cheapest model: {cheapest['model_id']} (${cheapest.get('total_cost', 0):.4f})")
        
        # Print successful models by provider
        if successful:
            providers = {}
            for result in successful:
                provider = result.get("provider", "Unknown")
                if provider not in providers:
                    providers[provider] = []
                providers[provider].append(result.get("model_id"))
            
            print("\nSuccessful models by provider:")
            for provider, models in providers.items():
                print(f"  {provider}: {len(models)} models")
                for model in models[:3]:  # Only show first 3 models per provider
                    print(f"    - {model}")
                if len(models) > 3:
                    print(f"    - ... and {len(models) - 3} more")

def main():
    """Main function to test models and update model information."""
    tester = ModelTester()
    
    # Test all models in vision_model_info.json
    results = tester.test_models()
    
    # Save results
    tester.save_results(results)
    
    # Update vision_model_info.json with test results
    tester.update_model_info(results)
    
    # Print summary
    tester.print_summary(results)

if __name__ == "__main__":
    main()