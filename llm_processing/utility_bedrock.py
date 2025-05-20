import boto3
import os

def check_available_models():
    """
    Checks available models in region
    """
    try:
        bedrock = boto3.client(
            'bedrock',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Get all models in region
        all_models = bedrock.list_foundation_models()
        
        print("\nModel Availability Status:")
        print("========================")
        
        for model in all_models.get('modelSummaries', []):
            model_id = model.get('modelId', 'Unknown')
            print(f"\nModel ID: {model_id}")
            print(f"Provider: {model.get('providerName', 'Unknown')}")
            print(f"Name: {model.get('modelName', 'Unknown')}")
            print(f"Status: {model.get('modelLifecycle', {}).get('status', 'Unknown')}")
            if 'inputModalities' in model:
                print(f"Input Modalities: {', '.join(model['inputModalities'])}")
            if 'outputModalities' in model:
                print(f"Output Modalities: {', '.join(model['outputModalities'])}")
            
    except Exception as e:
        print(f"Error checking models: {str(e)}")

# Example usage
check_available_models()
