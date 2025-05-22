import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


import boto3
import base64
import json
import time
import os
import re
from typing import Dict, Any, Tuple, Optional
from botocore.exceptions import ClientError
from llm_processing.llm_interface import ImageProcessor
from llm_processing.bedrock.utilities.base64_filter import filter_base64, filter_base64_from_dict

class BedrockImageProcessor(ImageProcessor):
    def __init__(self, api_key, prompt_name, prompt_text, model, modelname):
        super().__init__(api_key, prompt_name, prompt_text, model, modelname)
        self.bedrock_client = boto3.client("bedrock-runtime")
        self.bedrock_mgmt = boto3.client("bedrock")
        self.model_info = None
        self.account_id = self._get_account_id()
        self.set_token_costs_per_mil()
        print(f"BedrockImageProcessor initialized with model: {self.model}")
    
    def _get_account_id(self) -> str:
        """Get the AWS account ID."""
        try:
            sts_client = boto3.client('sts')
            return sts_client.get_caller_identity()["Account"]
        except Exception as e:
            print(f"Error getting AWS account ID: {str(e)}")
            return ""
    
    def set_token_costs_per_mil(self):
        """Set token costs based on the model provider."""
        provider = self.model.split(".")[0] if "." in self.model else ""
        
        # Default costs
        self.input_cost_per_mil = 1.0
        self.output_cost_per_mil = 2.0
        
        # Provider-specific costs
        if provider == "anthropic":
            self.input_cost_per_mil = 8.0
            self.output_cost_per_mil = 24.0
        elif provider == "amazon":
            self.input_cost_per_mil = 0.8
            self.output_cost_per_mil = 1.6
        elif provider == "mistral":
            self.input_cost_per_mil = 7.0
            self.output_cost_per_mil = 20.0
        elif provider == "meta":
            self.input_cost_per_mil = 6.0
            self.output_cost_per_mil = 6.0
    
    def supports_image_processing(self) -> bool:
        """Check if the selected model supports image processing."""
        # Load model info if not already loaded
        if not self.model_info:
            self.model_info = self.load_model_info()
        
        # Check if the model is in our image models list
        return self.model_info is not None
    
    def load_model_info(self) -> Dict[str, Any]:
        """Load model information from vision_model_info.json."""
        try:
            # Try to load from model_info directory first
            try:
                with open("llm_processing/bedrock/model_info/vision_model_info.json", "r") as f:
                    models = json.load(f)
                    for model in models:
                        if model.get("modelId") == self.model:
                            return model
                    return None
            except FileNotFoundError:
                # Fall back to root directory
                with open("vision_model_info.json", "r") as f:
                    models = json.load(f)
                    for model in models:
                        if model.get("modelId") == self.model:
                            return model
                    return None
        except Exception as e:
            print(f"Error loading model info: {str(e)}")
            return None
    
    def format_prompt(self, base64_image: str) -> Dict[str, Any]:
        """Format the prompt based on the model provider."""
        # Default implementation for models that don't have a specific formatter
        # Add a request for JSON output to the prompt text if not already present
        prompt_text = self.prompt_text
        if "json" not in prompt_text.lower():
            prompt_text += "\n\nPlease provide the transcription as a JSON object with a 'transcription' field."
        
        # Generic format that works with most models
        return {
            "inputText": prompt_text,
            "inputImage": base64_image,
            "textGenerationConfig": {
                "maxTokenCount": 4096,
                "temperature": 0.7,
                "topP": 0.9
            }
        }
    
    def extract_text(self, response_body: Dict[str, Any]) -> str:
        """Extract text from response."""
        # Default implementation for models that don't have a specific extractor
        # Try common response formats
        try:
            # Check for common response structures
            if "content" in response_body and isinstance(response_body["content"], list):
                # Claude-like format
                for item in response_body["content"]:
                    if isinstance(item, dict) and "text" in item:
                        return item.get("text", "")
            
            elif "output" in response_body:
                # Nova-like format
                output = response_body["output"]
                if isinstance(output, dict) and "message" in output:
                    message = output["message"]
                    if isinstance(message, dict) and "content" in message:
                        for item in message["content"]:
                            if isinstance(item, dict) and "text" in item:
                                return item.get("text", "")
            
            elif "results" in response_body and isinstance(response_body["results"], list):
                # Amazon-like format
                return response_body["results"][0].get("outputText", "")
            
            elif "generation" in response_body:
                # Meta-like format
                return response_body.get("generation", "")
            
            elif "text" in response_body:
                # Simple format
                return response_body.get("text", "")
            
            # If we can't find a known structure, convert the whole response to a string
            return json.dumps(response_body)
        
        except Exception as e:
            print(f"Error extracting text from response: {str(e)}")
            return f"Error extracting text: {str(e)}"
    
    def needs_inference_profile(self) -> bool:
        """Check if the model requires an inference profile."""
        if not self.model_info:
            return False
        
        inference_types = self.model_info.get("inferenceTypesSupported", [])
        return "INFERENCE_PROFILE" in inference_types
        return "INFERENCE_PROFILE" in inference_types and "ON_DEMAND" not in inference_types
    
    def get_inference_profile_id(self) -> str:
        """Get the inference profile ID for the model."""
        # For models that require inference profiles, construct the ARN
        if self.needs_inference_profile() and self.account_id:
            # Extract region from the client configuration
            region = self.bedrock_client.meta.region_name
            region_prefix = region.split('-')[0]  # e.g., "us" from "us-east-1"
            
            # Get provider from model ID
            provider = self.model.split('.')[0] if '.' in self.model else ""
            
            # Construct the inference profile ARN with region prefix
            # Format: arn:aws:bedrock:{region}:{account_id}:inference-profile/{region_prefix}.{model_id}
            return f"arn:aws:bedrock:{region}:{self.account_id}:inference-profile/{region_prefix}.{self.model}"
        
        return self.model
    
    def process_image(self, base64_image: str, image_name: str, image_index: int) -> Tuple[str, Dict[str, Any]]:
        # transcript_text, costs = processor.process_image(base64_image, image_ref, image_ref_idx)
        """Process an image with the selected model and return the transcription."""
        if not self.supports_image_processing():
            raise ValueError(f"Model {self.model} does not support image processing")
        
        start_time = time.time()
        
        # Format the prompt
        request_body = self.format_prompt(base64_image)
        
        # Get provider from model ID
        provider = self.model.split(".")[0] if "." in self.model else ""
        
        # Process differently based on provider
        try:
            # Check if we need to use an inference profile
            if self.needs_inference_profile():
                print(f"Using inference profile for model {self.model}")
                if provider == "meta":
                    # For Meta models with inference profiles, use SageMaker Runtime
                    return self._process_with_sagemaker(request_body, base64_image, image_name, start_time)
                else:
                    # For other models with inference profiles, use Bedrock with profile ARN
                    return self._process_with_bedrock(request_body, base64_image, image_name, start_time)
            else:
                # For models without inference profiles, use standard Bedrock
                return self._process_with_bedrock(request_body, base64_image, image_name, start_time)
                
        except Exception as e:
            error_message = f"Error processing image: {str(e)}"
            print(error_message)
            return error_message, {"error": error_message}

    def convert_to_plain_text(self, d):
        if type(d) == dict:
            d = d["transcription"] if "transcription" in d else d["text"] if "text" in d else d
            return "\n".join(f"{k}: {v}" for k, v in d.items())
        elif type(d) == str and r"{" in d:
            inner_dict = d.split(r"{")[-1].split(r"}")[0]
            temp = re.sub(r"[\n\'\"]", "", inner_dict)
            lines = [line.strip() for line in temp.split(",")]
            return "\n".join(lines)
        else:
            return json.dumps(d)              
    
    def _process_with_bedrock(self, request_body: Dict[str, Any], base64_image: str, 
                             image_name: str, start_time: float) -> Tuple[str, Dict[str, Any]]:
        """Process an image using the Bedrock client."""
        # Determine if we need to use an inference profile
        model_id = self.get_inference_profile_id()
        
        # Invoke the model
        print(f"Invoking model with ID: {model_id}")
        try:
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response.get("body").read())
            
            # Save raw response
            self.save_raw_response(response_body, image_name)
            
            # Extract text from response

            text = self.extract_text(response_body)
            print(f"before convert_to_plain_text: {type(text) = }, {text = }")
            text = self.convert_to_plain_text(text)
            print(f"after convert_to_plain_text: {type(text) = }, {text = }")
            # Update token usage if available
            self.update_usage(response_body)
            
            # Calculate processing time
            time_elapsed = (time.time() - start_time) / 60  # in minutes
            processing_data = self.get_transcript_processing_data(time_elapsed)
            
            self.num_processed += 1
            
            return text, processing_data
        except Exception as e:
            error_message = f"Error invoking model {model_id}: {str(e)}"
            print(error_message)
            
            # Add more context to the error message
            if "AccessDeniedException" in str(e):
                error_message += "\nAccess denied: You may not have permissions to use this model or inference profile."
            elif "ValidationException" in str(e) and "inference profile" in str(e).lower():
                error_message += "\nInference profile error: The inference profile may not be set up correctly."
            elif "ResourceNotFoundException" in str(e):
                error_message += "\nResource not found: The model or inference profile may not exist."
            
            return error_message, {"error": error_message}
    
    def _process_with_sagemaker(self, request_body: Dict[str, Any], base64_image: str, 
                               image_name: str, start_time: float) -> Tuple[str, Dict[str, Any]]:
        """Process an image using the SageMaker Runtime client."""
        # Initialize SageMaker Runtime client
        sagemaker_runtime = boto3.client('sagemaker-runtime')
        
        # Create a valid endpoint name by replacing invalid characters
        # SageMaker endpoint names must match: ^[a-zA-Z0-9](-*[a-zA-Z0-9])*
        model_id_clean = self.model.replace(".", "-").replace(":", "-")
        endpoint_name = f"llama-{model_id_clean}"
        
        print(f"Invoking SageMaker endpoint: {endpoint_name}")
        
        try:
            # Invoke the endpoint
            response = sagemaker_runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType='application/json',
                Body=json.dumps(request_body)
            )
            
            # Process the response
            response_body = json.loads(response['Body'].read())
            
            # Save raw response
            self.save_raw_response(response_body, image_name)
            
            # Extract text from response
            text = self.extract_text(response_body)
            
            # Update token usage if available
            self.update_usage(response_body)
            
            # Calculate processing time
            time_elapsed = (time.time() - start_time) / 60  # in minutes
            processing_data = self.get_transcript_processing_data(time_elapsed)
            
            self.num_processed += 1
            
            return text, processing_data
        except Exception as e:
            error_message = f"Error invoking SageMaker endpoint {endpoint_name}: {str(e)}"
            print(error_message)
            
            # Add more context to the error message
            if "ValidationError" in str(e) and "not found" in str(e):
                error_message += "\nEndpoint not found: The SageMaker endpoint may not be set up for this model."
                error_message += "\nTo use this model, you need to set up a SageMaker endpoint with the name format: llama-{model-id}"
            elif "AccessDeniedException" in str(e):
                error_message += "\nAccess denied: You may not have permissions to use this SageMaker endpoint."
            
            return error_message, {"error": error_message}
    
    def update_usage(self, response_data: Dict[str, Any]):
        """Update token usage from response data."""
        # Default implementation for models that don't have a specific usage extractor
        try:
            # Check for common usage structures
            if "usage" in response_data:
                usage = response_data["usage"]
                
                # Try different key formats
                if "input_tokens" in usage:
                    self.input_tokens = usage.get("input_tokens", 0)
                elif "inputTokens" in usage:
                    self.input_tokens = usage.get("inputTokens", 0)
                elif "prompt_tokens" in usage:
                    self.input_tokens = usage.get("prompt_tokens", 0)
                elif "inputTokenCount" in usage:
                    self.input_tokens = usage.get("inputTokenCount", 0)
                
                if "output_tokens" in usage:
                    self.output_tokens = usage.get("output_tokens", 0)
                elif "outputTokens" in usage:
                    self.output_tokens = usage.get("outputTokens", 0)
                elif "completion_tokens" in usage:
                    self.output_tokens = usage.get("completion_tokens", 0)
                elif "outputTokenCount" in usage:
                    self.output_tokens = usage.get("outputTokenCount", 0)
        except Exception as e:
            print(f"Error updating usage: {str(e)}")

####### Testing Module  #######
import random
RANDOM_ERROR_THRESHOLD = 0.5
SAMPLE_DIRECTORY  = "raw_llm_responses"
SAMPLE_PROVIDER = "Claude 3.5 Sonnet"
SAMPLE_FILE = "Test_Image-2025-05-11-1951-39-raw.json"


class BedrockImageProcessorTesting(ImageProcessor):
    def __init__(self, api_key, prompt_name, prompt_text, model, modelname, include_random_error=True):
        super().__init__(api_key, prompt_name, prompt_text, model, modelname)
        self.bedrock_client = boto3.client("bedrock-runtime")
        self.bedrock_mgmt = boto3.client("bedrock")
        self.model_info = None
        self.account_id = self._get_account_id()
        self.set_token_costs_per_mil()
    
    def _get_account_id(self) -> str:
        """Get the AWS account ID."""
        try:
            sts_client = boto3.client('sts')
            return sts_client.get_caller_identity()["Account"]
        except Exception as e:
            print(f"Error getting AWS account ID: {str(e)}")
            return ""
    
    def set_token_costs_per_mil(self):
        """Set token costs based on the model provider."""
        provider = self.model.split(".")[0] if "." in self.model else ""
        # Default costs
        self.input_cost_per_mil = 1.0
        self.output_cost_per_mil = 2.0
        # Provider-specific costs
        if provider == "anthropic":
            self.input_cost_per_mil = 8.0
            self.output_cost_per_mil = 24.0
        elif provider == "amazon":
            self.input_cost_per_mil = 0.8
            self.output_cost_per_mil = 1.6
        elif provider == "mistral":
            self.input_cost_per_mil = 7.0
            self.output_cost_per_mil = 20.0
        elif provider == "meta":
            self.input_cost_per_mil = 6.0
            self.output_cost_per_mil = 6.0
    
    def load_model_info(self) -> Dict[str, Any]:
        """Load model information from vision_model_info.json."""
        try:
            try:
                with open("llm_processing/bedrock/model_info/vision_model_info.json", "r") as f:
                    models = json.load(f)
                    for model in models:
                        if model.get("modelId") == self.model:
                            return model
                    return None
            except FileNotFoundError:
                # Fall back to root directory
                with open("vision_model_info.json", "r") as f:
                    models = json.load(f)
                    for model in models:
                        if model.get("modelId") == self.model:
                            return model
                    return None
        except Exception as e:
            print(f"Error loading model info: {str(e)}")
            return None
    
    def format_prompt(self, base64_image: str) -> Dict[str, Any]:
        """Format the prompt based on the model provider."""
        # Default implementation for models that don't have a specific formatter
        # Add a request for JSON output to the prompt text if not already present
        prompt_text = self.prompt_text
        if "json" not in prompt_text.lower():
            prompt_text += "\n\nPlease provide the transcription as a JSON object with a 'transcription' field."
        
        # Generic format that works with most models
        return {
            "inputText": prompt_text,
            "inputImage": base64_image,
            "textGenerationConfig": {
                "maxTokenCount": 4096,
                "temperature": 0.7,
                "topP": 0.9
            }
        }
    
    def extract_text(self, response_body: Dict[str, Any]) -> str:
        """Extract text from response."""
        # Default implementation for models that don't have a specific extractor
        # Try common response formats
        try:
            # Check for common response structures
            if "content" in response_body and isinstance(response_body["content"], list):
                # Claude-like format
                for item in response_body["content"]:
                    if isinstance(item, dict) and "text" in item:
                        return item.get("text", "")
            
            elif "output" in response_body:
                # Nova-like format
                output = response_body["output"]
                if isinstance(output, dict) and "message" in output:
                    message = output["message"]
                    if isinstance(message, dict) and "content" in message:
                        for item in message["content"]:
                            if isinstance(item, dict) and "text" in item:
                                return item.get("text", "")
            
            elif "results" in response_body and isinstance(response_body["results"], list):
                # Amazon-like format
                return response_body["results"][0].get("outputText", "")
            
            elif "generation" in response_body:
                # Meta-like format
                return response_body.get("generation", "")
            
            elif "text" in response_body:
                # Simple format
                return response_body.get("text", "")
            
            # If we can't find a known structure, convert the whole response to a string
            return json.dumps(response_body)
        except Exception as e:
            print(f"Error extracting text from response: {str(e)}")
            return f"Error extracting text: {str(e)}"

    def load_sample_raw_response(self) -> Dict[str, Any]:
        """Load a sample raw response from a JSON file."""
        try:
            file_path = os.path.join(SAMPLE_DIRECTORY, SAMPLE_PROVIDER, SAMPLE_FILE)
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading sample raw response: {str(e)}")
            return {"error": f"Error loading sample raw response: {str(e)}"}        
    
    def process_image(self, base64_image: str, image_name: str, image_index: int) -> Tuple[str, Dict[str, Any]]:
        print(f"process_image called in testing mode: {image_name = }")
        start_time = time.time()
        try:
            if include_random_error and random.random() < RANDOM_ERROR_THRESHOLD:
                raise Exception("Hypothetical Random Error Occurred")
            response_body = self.load_sample_raw_response()
            self.update_usage(response_body)
            text = self.extract_text(response_body)
            time_elapsed = (time.time() - start_time) / 60  # in minutes
            processing_data = self.get_transcript_processing_data(time_elapsed)
            self.num_processed += 1    
            return text, processing_data
        except Exception as e:
            error_message = f"Error processing image: {str(e)}"
            print(error_message)
            return error_message, {"error": error_message}
    
    def update_usage(self, response_data: Dict[str, Any]):
        """Update token usage from response data."""
        # Default implementation for models that don't have a specific usage extractor
        try:
            # Check for common usage structures
            if "usage" in response_data:
                usage = response_data["usage"]
                
                # Try different key formats
                if "input_tokens" in usage:
                    self.input_tokens = usage.get("input_tokens", 0)
                elif "inputTokens" in usage:
                    self.input_tokens = usage.get("inputTokens", 0)
                elif "prompt_tokens" in usage:
                    self.input_tokens = usage.get("prompt_tokens", 0)
                elif "inputTokenCount" in usage:
                    self.input_tokens = usage.get("inputTokenCount", 0)
                
                if "output_tokens" in usage:
                    self.output_tokens = usage.get("output_tokens", 0)
                elif "outputTokens" in usage:
                    self.output_tokens = usage.get("outputTokens", 0)
                elif "completion_tokens" in usage:
                    self.output_tokens = usage.get("completion_tokens", 0)
                elif "outputTokenCount" in usage:
                    self.output_tokens = usage.get("outputTokenCount", 0)
        except Exception as e:
            print(f"Error updating usage: {str(e)}")

########## End Testing Module  #############

class ClaudeImageProcessor(BedrockImageProcessor):
    """Specialized processor for Claude models."""
    
    def format_prompt(self, base64_image: str) -> Dict[str, Any]:
        """Format the prompt for Claude models."""
        # Add a request for JSON output to the prompt text if not already present
        prompt_text = self.prompt_text
        if "json" not in prompt_text.lower():
            prompt_text += "\n\nPlease provide the transcription as a JSON object with a 'transcription' field."
        
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt_text
                        }
                    ]
                }
            ]
        }
    
    def update_usage(self, response_data: Dict[str, Any]):
        """Update token usage from Claude response data."""
        usage = response_data.get("usage", {})
        self.input_tokens = usage.get("input_tokens", 0)
        self.output_tokens = usage.get("output_tokens", 0)
    
    def extract_text(self, response_body: Dict[str, Any]) -> str:
        """Extract text from Claude response."""
        content = response_body.get("content", [])
        text = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
        
        # Try to extract JSON from the text if it contains JSON markers
        if "{" in text and "}" in text:
            try:
                # Find JSON content between curly braces
                import re
                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    # Validate it's proper JSON by parsing it
                    json.loads(json_str)
                    # If successful, return just the JSON part
                    return json_str
            except json.JSONDecodeError:
                # If JSON parsing fails, return the full text
                pass
        
        return text


class NovaImageProcessor(BedrockImageProcessor):
    """Specialized processor for Amazon Nova models."""
    
    def format_prompt(self, base64_image: str) -> Dict[str, Any]:
        """Format the prompt for Nova models."""
        # Add a request for JSON output to the prompt text if not already present
        prompt_text = self.prompt_text
        if "json" not in prompt_text.lower():
            prompt_text += "\n\nPlease provide the transcription as a JSON object with a 'transcription' field."
        
        # Based on debug_nova.py results, format 1 works for Nova models
        return {
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
                        "text": prompt_text
                    }
                ],
            }],
            "inferenceConfig": {"max_new_tokens": 4096, "top_p": 0.9, "temperature": 0.0}
        }
    
    def update_usage(self, response_data: Dict[str, Any]):
        """Update token usage from Nova response data."""
        usage = response_data.get("usage", {})
        self.input_tokens = usage.get("inputTokens", 0)
        self.output_tokens = usage.get("outputTokens", 0)
    
    def extract_text(self, response_body: Dict[str, Any]) -> str:
        """Extract text from Nova response."""
        try:
            # Try to extract from the output.message.content structure
            if "output" in response_body and "message" in response_body["output"]:
                message = response_body["output"]["message"]
                if "content" in message and isinstance(message["content"], list):
                    for item in message["content"]:
                        if isinstance(item, dict) and "text" in item:
                            return item["text"]
            
            # Fall back to old format
            return response_body.get("results", [{}])[0].get("outputText", "")
        except Exception as e:
            # Import base64_filter here to avoid circular imports
            from utilities.base64_filter import filter_base64
            filtered_response = filter_base64(str(response_body))
            print(f"Error extracting text from Nova response: {str(e)}")
            return f"Error parsing response: {filtered_response[:500]}"


class AmazonImageProcessor(BedrockImageProcessor):
    """Specialized processor for other Amazon models (Titan, etc.)."""
    
    def format_prompt(self, base64_image: str) -> Dict[str, Any]:
        """Format the prompt for Amazon models."""
        return {
            "inputText": self.prompt_text,
            "inputImage": base64_image,
            "textGenerationConfig": {
                "maxTokenCount": 4096,
                "temperature": 0.7,
                "topP": 0.9
            }
        }
    
    def update_usage(self, response_data: Dict[str, Any]):
        """Update token usage from Amazon response data."""
        usage = response_data.get("usage", {})
        self.input_tokens = usage.get("inputTokenCount", 0)
        self.output_tokens = usage.get("outputTokenCount", 0)
    
    def extract_text(self, response_body: Dict[str, Any]) -> str:
        """Extract text from Amazon response."""
        return response_body.get("results", [{}])[0].get("outputText", "")


class MetaImageProcessor(BedrockImageProcessor):
    """Specialized processor for Meta models."""
    
    def format_prompt(self, base64_image: str) -> Dict[str, Any]:
        """Format the prompt for Meta models."""
        return {
            "prompt": self.prompt_text,
            "image": base64_image
        }
    
    def update_usage(self, response_data: Dict[str, Any]):
        """Update token usage from Meta response data."""
        usage = response_data.get("usage", {})
        self.input_tokens = usage.get("input_tokens", 0)
        self.output_tokens = usage.get("output_tokens", 0)
    
    def extract_text(self, response_body: Dict[str, Any]) -> str:
        """Extract text from Meta response."""
        return response_body.get("generation", "") or response_body.get("text", "")
    
    def process_image(self, base64_image: str, image_name: str, image_index: int) -> Tuple[str, Dict[str, Any]]:
        """Process an image with Meta model using SageMaker."""
        if not self.supports_image_processing():
            raise ValueError(f"Model {self.model} does not support image processing")
        
        start_time = time.time()
        
        # Format the prompt
        request_body = self.format_prompt(base64_image)
        
        # Use SageMaker for Meta models
        return self._process_with_sagemaker(request_body, base64_image, image_name, start_time)


class MistralImageProcessor(BedrockImageProcessor):
    """Specialized processor for Mistral models."""
    
    def format_prompt(self, base64_image: str) -> Dict[str, Any]:
        """Format the prompt for Mistral models."""
        return {
            "prompt": self.prompt_text,
            "image": base64_image,
            "max_tokens": 4096
        }
    
    def update_usage(self, response_data: Dict[str, Any]):
        """Update token usage from Mistral response data."""
        usage = response_data.get("usage", {})
        self.input_tokens = usage.get("prompt_tokens", 0)
        self.output_tokens = usage.get("completion_tokens", 0)
    
    def extract_text(self, response_body: Dict[str, Any]) -> str:
        """Extract text from Mistral response."""
        return response_body.get("outputs", [{}])[0].get("text", "")


# Factory function to create the appropriate processor
def create_image_processor(api_key, prompt_name, prompt_text, model, modelname):
    """Create the appropriate image processor based on the model."""
    provider = model.split(".")[0] if "." in model else ""
    
    # Load model info to check if it has an inference profile
    model_info = None
    try:
        # Try to load from model_info directory first
        try:
            with open("llm_processing/bedrock/model_info/vision_model_info.json", "r") as f:
                models = json.load(f)
                for m in models:
                    if m.get("modelId") == model:
                        model_info = m
                        break
        except FileNotFoundError:
            # Fall back to root directory
            with open("vision_model_info.json", "r") as f:
                models = json.load(f)
                for m in models:
                    if m.get("modelId") == model:
                        model_info = m
                        break
    except Exception as e:
        print(f"Error loading model info: {str(e)}")
    
    # Create the appropriate processor based on provider
    try:
        if provider == "anthropic":
            return ClaudeImageProcessor(api_key, prompt_name, prompt_text, model, modelname)
        elif provider == "meta":
            return MetaImageProcessor(api_key, prompt_name, prompt_text, model, modelname)
        elif provider == "mistral":
            return MistralImageProcessor(api_key, prompt_name, prompt_text, model, modelname)
        elif provider == "amazon":
            if "nova" in model.lower():
                return NovaImageProcessor(api_key, prompt_name, prompt_text, model, modelname)
            else:
                return AmazonImageProcessor(api_key, prompt_name, prompt_text, model, modelname)
        else:
            # Default to base class for other providers
            print(f"Using default processor for model: {model} (provider: {provider})")
            return BedrockImageProcessor(api_key, prompt_name, prompt_text, model, modelname)
    except Exception as e:
        print(f"Error creating processor for model {model}: {str(e)}")
        # Fallback to base class if there's an error
        return BedrockImageProcessor(api_key, prompt_name, prompt_text, model, modelname)