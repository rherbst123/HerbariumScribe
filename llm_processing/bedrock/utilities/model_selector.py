import boto3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

class ModelSelector:
    def __init__(self):
        self.bedrock_client = boto3.client("bedrock-runtime")
        self.bedrock_mgmt = boto3.client("bedrock")
        self.model_info_schema = {
            "model_id": "",
            "provider": "",
            "model_name": "",
            "supports_image": False,
            "max_tokens": 0,
            "pricing": {
                "input": 0.0,
                "output": 0.0
            },
            "capabilities": [],
            "use_inference_profile": False,
            "inference_profile_arn": ""
        }
    
    def get_available_models(self) -> List[str]:
        response = self.bedrock_mgmt.list_foundation_models()
        models = []
        
        for model in response.get("modelSummaries", []):
            model_id = model.get("modelId")
            if model_id:
                models.append(model_id)
                
        return models
    
    def check_image_support(self, model_id: str, input_modalities: List[str] = None) -> bool:
        # If we have input modalities from the API, use that information
        if input_modalities:
            return "IMAGE" in input_modalities
            
        # Fallback to checking by provider name
        image_capable_providers = ["anthropic", "meta", "amazon", "mistral"]
        for provider in image_capable_providers:
            if provider in model_id.lower():
                return True
        return False
    
    def get_model_provider(self, model_id: str) -> str:
        if "." in model_id:
            return model_id.split(".")[0]
        return "unknown"
    
    def get_model_name(self, model_id: str) -> str:
        if "." in model_id:
            parts = model_id.split(".")
            if len(parts) > 1:
                return parts[1].split("-")[0]
        return model_id
    
    def get_model_details(self, model_id: str) -> Dict[str, Any]:
        try:
            response = self.bedrock_mgmt.get_foundation_model(
                modelIdentifier=model_id
            )
            
            model_details = response.get("modelDetails", {})
            
            details = {
                "model_name": model_details.get("modelName", ""),
                "provider_name": model_details.get("providerName", ""),
                "input_modalities": model_details.get("inputModalities", []),
                "output_modalities": model_details.get("outputModalities", []),
                "streaming_supported": model_details.get("responseStreamingSupported", False),
                "customizations_supported": model_details.get("customizationsSupported", []),
                "inference_types": model_details.get("inferenceTypesSupported", []),
                "lifecycle_status": model_details.get("modelLifecycle", {}).get("status", ""),
                "model_arn": model_details.get("modelArn", "")
            }
            
            return details
        except Exception as e:
            print(f"Error getting model details for {model_id}: {str(e)}")
            return {}
            
    def get_inference_profile_arn(self, model_id: str, model_details: Dict[str, Any] = None) -> Optional[str]:
        try:
            # First, check if the model supports inference profiles
            if not model_details:
                response = self.bedrock_mgmt.get_foundation_model(
                    modelIdentifier=model_id
                )
                model_details = response.get("modelDetails", {})
            
            inference_types = model_details.get("inferenceTypesSupported", [])
            
            # If the model doesn't support inference profiles, return None
            if "INFERENCE_PROFILE" not in inference_types:
                return None
                
            # List inference profiles to find one for this model
            try:
                profiles_response = self.bedrock_mgmt.list_inference_profiles()
                for profile in profiles_response.get("inferenceProfiles", []):
                    # Check if this profile is for our model
                    if profile.get("modelId") == model_id:
                        # Return the full ARN of the inference profile
                        profile_arn = profile.get("inferenceProfileArn")
                        print(f"Found inference profile ARN for {model_id}: {profile_arn}")
                        return profile_arn
                
                print(f"No matching inference profile found for {model_id}")
            except Exception as e:
                print(f"Error listing inference profiles: {str(e)}")
                
            # Fallback to model ARN if no profile found
            model_arn = model_details.get("modelArn", "")
            print(f"Using model ARN as fallback for {model_id}: {model_arn}")
            return model_arn
        except Exception as e:
            print(f"Error getting inference profile for {model_id}: {str(e)}")
            return None
    
    def preliminary_model_setup(self):
        models = self.get_available_models()
        model_info = {}
        
        # Example response for Mistral Pixtral model
        mistral_example = {
            'modelDetails': {
                'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/mistral.pixtral-large-2502-v1:0',
                'modelId': 'mistral.pixtral-large-2502-v1:0',
                'modelName': 'Pixtral Large (25.02)',
                'providerName': 'Mistral AI',
                'inputModalities': ['TEXT', 'IMAGE'],
                'outputModalities': ['TEXT'],
                'responseStreamingSupported': True,
                'customizationsSupported': [],
                'inferenceTypesSupported': ['INFERENCE_PROFILE'],
                'modelLifecycle': {'status': 'ACTIVE'}
            }
        }
        
        # Add the Mistral model from the example response
        mistral_id = mistral_example['modelDetails']['modelId']
        if mistral_id not in models:
            models.append(mistral_id)
        
        # First, try to get all inference profiles at once to avoid repeated API calls
        inference_profiles = {}
        try:
            profiles_response = self.bedrock_mgmt.list_inference_profiles()
            for profile in profiles_response.get("inferenceProfiles", []):
                model_id = profile.get("modelId")
                if model_id:
                    inference_profiles[model_id] = profile.get("inferenceProfileArn")
                    print(f"Found inference profile for {model_id}: {profile.get('inferenceProfileArn')}")
        except Exception as e:
            print(f"Error listing inference profiles: {str(e)}")
        
        for model_id in models:
            # Special case for the Mistral model from the example
            if model_id == mistral_id:
                details = {
                    "model_name": mistral_example['modelDetails']['modelName'],
                    "provider_name": mistral_example['modelDetails']['providerName'],
                    "input_modalities": mistral_example['modelDetails']['inputModalities'],
                    "output_modalities": mistral_example['modelDetails']['outputModalities'],
                    "streaming_supported": mistral_example['modelDetails']['responseStreamingSupported'],
                    "customizations_supported": mistral_example['modelDetails']['customizationsSupported'],
                    "inference_types": mistral_example['modelDetails']['inferenceTypesSupported'],
                    "lifecycle_status": mistral_example['modelDetails']['modelLifecycle']['status'],
                    "model_arn": mistral_example['modelDetails']['modelArn']
                }
            else:
                details = self.get_model_details(model_id)
            
            provider = details.get("provider_name") or self.get_model_provider(model_id)
            model_name = details.get("model_name") or self.get_model_name(model_id)
            supports_image = self.check_image_support(model_id, details.get("input_modalities"))
            
            # Get inference profile ARN if available
            inference_profile_arn = inference_profiles.get(model_id)
            if not inference_profile_arn:
                # If not found in the pre-fetched list, try to get it individually
                inference_profile_arn = self.get_inference_profile_arn(model_id, details)
            
            model_data = {
                "model_id": model_id,
                "provider": provider,
                "model_name": model_name,
                "supports_image": supports_image,
                "input_modalities": details.get("input_modalities", []),
                "output_modalities": details.get("output_modalities", []),
                "streaming_supported": details.get("streaming_supported", False),
                "lifecycle_status": details.get("lifecycle_status", ""),
                "max_tokens": 0,  # Would need to be populated from documentation or API
                "pricing": {
                    "input": 0.0,  # Would need to be populated from documentation or API
                    "output": 0.0  # Would need to be populated from documentation or API
                },
                "capabilities": ["text"] + (["image"] if supports_image else [])
            }
            
            # Add inference profile ARN if available
            if inference_profile_arn:
                model_data["inference_profile_arn"] = inference_profile_arn
                model_data["use_inference_profile"] = True
            else:
                model_data["use_inference_profile"] = False
            
            model_info[model_id] = model_data
        
        # Save to JSON file
        output_path = Path("model_info.json")
        with open(output_path, "w") as f:
            json.dump(model_info, f, indent=2)
            
        print(f"Model information saved to {output_path}")
        return model_info

    def filter_image_and_inference_ready(self, model_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Filter models that support both image processing and inference profiles.
        
        Args:
            model_info: Optional dictionary of model information. If not provided,
                        will run preliminary_model_setup to get the information.
        
        Returns:
            Dictionary of models that support both image processing and inference profiles.
        """
        if model_info is None:
            model_info = self.preliminary_model_setup()
        
        filtered_models = {}
        
        for model_id, model_data in model_info.items():
            if (model_data.get("supports_image", False) and 
                model_data.get("use_inference_profile", False) and
                model_data.get("inference_profile_arn", "")):  # Make sure ARN exists
                filtered_models[model_id] = model_data
        
        return filtered_models

if __name__ == "__main__":
    selector = ModelSelector()
    all_models = selector.preliminary_model_setup()
    
    # Get models that support both image processing and inference profiles
    image_inference_models = selector.filter_image_and_inference_ready(all_models)
    
    print(f"\nFound {len(image_inference_models)} models that support both image processing and inference profiles:")
    for model_id in image_inference_models:
        print(f"- {model_id}")