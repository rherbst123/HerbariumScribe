#!/usr/bin/env python3
"""
Test a single model for image processing capabilities.
"""

from model_tester import ModelTester

def main():
    """Test a single model for image processing capabilities."""
    tester = ModelTester()
    
    # Load all models
    all_models = tester.load_models()
    
    # Filter for Claude 3.5 Sonnet
    claude_models = [m for m in all_models if m.get('modelId') == 'anthropic.claude-3-5-sonnet-20240620-v1:0']
    
    if not claude_models:
        print("Claude 3.5 Sonnet model not found.")
        return
    
    # Test the model
    results = tester.test_models(claude_models)
    
    # Update vision_model_info.json with test results
    tester.update_model_info(results)
    
    # Print summary
    tester.print_summary(results)

if __name__ == "__main__":
    main()