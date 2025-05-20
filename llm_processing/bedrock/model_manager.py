#!/usr/bin/env python3
"""
Model Manager for Field Museum Bedrock Transcription application.
This module handles model discovery, information retrieval, and testing.
"""

import boto3
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

class ModelManager:
    """Manages AWS Bedrock models, their information, and testing."""
    
    def __init__(self):
        """Initialize the ModelManager."""
        self.bedrock_client = boto3.client("bedrock-runtime")
        self.bedrock_mgmt = boto3.client("bedrock")
        self.account_id = self._get_account_id()
        self.region = self.bedrock_client.meta.region_name
        self.region_prefix = self.region.split('-')[0]  # e.g., "us" from "us-east-1"
        
        # Pricing information per million tokens
        self.pricing = {
            "anthropic": {"input": 8.0, "output": 24.0},
            "amazon": {"input": 0.8, "output": 1.6},
            "meta": {"input": 6.0, "output": 6.0},
            "mistral": {"input": 7.0, "output": 20.0},
            "cohere": {"input": 3.0, "output": 6.0},
            "ai21": {"input": 4.0, "output": 8.0},
            "stability": {"input": 0.0, "output": 0.0}
        }
        
        # Default pricing for unknown providers
        self.default_pricing = {"input": 1.0, "output": 2.0}
    
    def _get_account_id(self) -> str:
        """Get the AWS account ID."""
        try:
            sts_client = boto3.client('sts')
            return sts_client.get_caller_identity()["Account"]
        except Exception as e:
            print(f"Error getting AWS account ID: {str(e)}")
            return ""
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get all available foundation models from AWS Bedrock."""
        try:
            response = self.bedrock_mgmt.list_foundation_models()
            return response.get("modelSummaries", [])
        except Exception as e:
            print(f"Error listing foundation models: {str(e)}")
            return []
    
    def get_model_details(self, model_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific model."""
        try:
            response = self.bedrock_mgmt.get_foundation_model(
                modelIdentifier=model_id
            )
            return response.get("modelDetails", {})
        except Exception as e:
            print(f"Error getting model details for {model_id}: {str(e)}")
            return {}
    
    def get_inference_profiles(self) -> List[Dict[str, Any]]:
        """Get all available inference profiles."""
        try:
            response = self.bedrock_mgmt.list_inference_profiles()
            return response.get("inferenceProfiles", [])
        except Exception as e:
            print(f"Error listing inference profiles: {str(e)}")
            return []
    
    def get_model_pricing(self, provider: str) -> Dict[str, float]:
        """Get pricing information for a provider."""
        return self.pricing.get(provider, self.default_pricing)
    
    def supports_image_processing(self, model_details: Dict[str, Any]) -> bool:
        """Check if a model supports image processing based on its details."""
        input_modalities = model_details.get("inputModalities", [])
        return "IMAGE" in input_modalities
    
    def get_inference_profile_arn(self, model_id: str) -> Optional[str]:
        """Get the ARN for an inference profile if available."""
        profiles = self.get_inference_profiles()
        
        for profile in profiles:
            if profile.get("modelId") == model_id:
                return profile.get("inferenceProfileArn")
        
        # If no profile found, construct a potential ARN
        if self.account_id:
            return f"arn:aws:bedrock:{self.region}:{self.account_id}:inference-profile/{self.region_prefix}.{model_id}"
        
        return None
    
    def build_model_info(self) -> List[Dict[str, Any]]:
        """Build comprehensive information about all available models."""
        models_info = []
        
        # Get all available models
        available_models = self.get_available_models()
        
        # Get all inference profiles
        inference_profiles = self.get_inference_profiles()
        profile_map = {profile.get("modelId"): profile for profile in inference_profiles}
        
        # Process each model
        for model_summary in available_models:
            model_id = model_summary.get("modelId")
            if not model_id:
                continue
            
            # Get detailed information about the model
            model_details = self.get_model_details(model_id)
            
            # Extract provider name
            provider_name = model_details.get("providerName", "")
            provider_key = provider_name.lower().split()[0] if provider_name else ""
            
            # Check if model supports image processing
            supports_image = self.supports_image_processing(model_details)
            
            # Get inference types
            inference_types = model_details.get("inferenceTypesSupported", [])
            
            # Get pricing information
            pricing = self.get_model_pricing(provider_key)
            
            # Check if model has an inference profile
            inference_profile_arn = None
            if model_id in profile_map:
                inference_profile_arn = profile_map[model_id].get("inferenceProfileArn")
            
            # Build model information
            model_info = {
                "modelId": model_id,
                "modelName": model_details.get("modelName", ""),
                "provider": provider_name,
                "supports_image": supports_image,
                "input_modalities": model_details.get("inputModalities", []),
                "output_modalities": model_details.get("outputModalities", []),
                "streaming_supported": model_details.get("responseStreamingSupported", False),
                "lifecycle_status": model_details.get("modelLifecycle", {}).get("status", ""),
                "inferenceTypes": inference_types,
                "pricing": pricing,
                "use_inference_profile": "INFERENCE_PROFILE" in inference_types,
                "on_demand_supported": "ON_DEMAND" in inference_types
            }
            
            # Add inference profile ARN if available
            if inference_profile_arn:
                model_info["inference_profile_arn"] = inference_profile_arn
            
            models_info.append(model_info)
        
        return models_info
    
    def save_model_info(self, output_path: str = "model_info.json") -> None:
        """Save model information to a JSON file."""
        models_info = self.build_model_info()
        
        # Ensure model_info directory exists
        os.makedirs("model_info", exist_ok=True)
        
        # Save to model_info directory
        model_info_path = os.path.join("model_info", output_path)
        with open(model_info_path, "w") as f:
            json.dump(models_info, f, indent=2)
        
        print(f"Model information saved to {model_info_path}")
    
    def save_vision_model_info(self, output_path: str = "vision_model_info.json") -> None:
        """Save information about models that support image processing to a JSON file."""
        all_models = self.build_model_info()
        
        # Filter for models that support image processing
        vision_models = [model for model in all_models if model.get("supports_image", False)]
        
        # Ensure model_info directory exists
        os.makedirs("model_info", exist_ok=True)
        
        # Save to model_info directory
        vision_model_info_path = os.path.join("model_info", output_path)
        with open(vision_model_info_path, "w") as f:
            json.dump(vision_models, f, indent=2)
        
        print(f"Vision model information saved to {vision_model_info_path}")
        print(f"Found {len(vision_models)} models that support image processing")
        
        # Print some statistics
        providers = set(model.get("provider", "") for model in vision_models)
        print(f"Providers: {', '.join(providers)}")
        
        inference_profile_models = [model for model in vision_models if model.get("use_inference_profile", False)]
        print(f"Models with inference profiles: {len(inference_profile_models)}")
        
        on_demand_models = [model for model in vision_models if model.get("on_demand_supported", False)]
        print(f"Models with on-demand support: {len(on_demand_models)}")

def main():
    """Main function to build and save model information."""
    manager = ModelManager()
    
    # Save all model information
    manager.save_model_info()
    
    # Save vision model information
    manager.save_vision_model_info()

if __name__ == "__main__":
    main()