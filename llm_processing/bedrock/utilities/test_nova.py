#!/usr/bin/env python3
"""
Test Nova models for image processing capabilities.
"""

from model_tester import ModelTester

def main():
    """Test Nova models for image processing capabilities."""
    tester = ModelTester()
    
    # Load all models
    all_models = tester.load_models()
    
    # Filter for Nova models
    nova_models = [m for m in all_models if "nova" in m.get('modelId', '').lower()]
    
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