#!/usr/bin/env python
"""
Script to regenerate the model_info.json file with correct inference profile ARNs.
"""

from model_selector import ModelSelector

def main():
    print("Regenerating model_info.json with correct inference profile ARNs...")
    selector = ModelSelector()
    model_info = selector.preliminary_model_setup()
    
    # Count models with inference profiles
    inference_models = [m for m in model_info.values() if m.get("use_inference_profile", False)]
    image_models = [m for m in model_info.values() if m.get("supports_image", False)]
    image_inference_models = [m for m in model_info.values() 
                             if m.get("supports_image", False) and 
                                m.get("use_inference_profile", False) and
                                m.get("inference_profile_arn", "")]
    
    print(f"Total models: {len(model_info)}")
    print(f"Models with inference profiles: {len(inference_models)}")
    print(f"Models with image support: {len(image_models)}")
    print(f"Models with both image support and inference profiles: {len(image_inference_models)}")
    
    if image_inference_models:
        print("\nModels that support both image processing and inference profiles:")
        for model in image_inference_models:
            print(f"- {model['model_id']}")
            print(f"  ARN: {model.get('inference_profile_arn', 'No ARN found')}")
    else:
        print("\nNo models found that support both image processing and inference profiles.")
    
    print("\nDone! model_info.json has been updated.")

if __name__ == "__main__":
    main()