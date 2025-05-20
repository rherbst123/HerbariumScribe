import boto3
import json

def get_image_input_models(response):
    image_models = []
    try:
        for model in response['modelSummaries']:
            if 'IMAGE' in model.get('inputModalities', []):
                image_models.append({
                    'modelId': model['modelId'],
                    'modelName': model['modelName'],
                    'provider': model['providerName'],
                    'inferenceTypes': model.get('inferenceTypesSupported', [])
                })
        return image_models
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return []

def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
        

def main():
    bedrock_client = boto3.client('bedrock')
    response = bedrock_client.list_foundation_models()
    image_models = get_image_input_models(response)
    save_to_json(image_models, 'image_models.json')
    for model in image_models:
        print(f"Model ID: {model['modelId']}")
        print(f"Model Name: {model['modelName']}")
        print(f"Provider: {model['provider']}")
        print(f"Inference Types: {model['inferenceTypes']}")
        print("---")        

if __name__ == "__main__":
    main()