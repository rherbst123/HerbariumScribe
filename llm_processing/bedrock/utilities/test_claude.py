#!/usr/bin/env python3
"""
Test Claude models for image processing capabilities.
"""

from model_tester import ModelTester

def main():
    """Test Claude models for image processing capabilities."""
    tester = ModelTester()
    
    # Load all models
    all_models = tester.load_models()
    
    # Filter for Claude models
    claude_models = [m for m in all_models if "claude" in m.get('modelId', '').lower()]
    
    if not claude_models:
        print("No Claude models found.")
        return
    
    print(f"Found {len(claude_models)} Claude models.")
    
    # Test the models
    results = tester.test_models(claude_models)
    
    # Update vision_model_info.json with test results
    tester.update_model_info(results)
    
    # Print summary
    tester.print_summary(results)

if __name__ == "__main__":
    main()