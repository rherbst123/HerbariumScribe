import anthropic
import base64
import requests
from PIL import Image
from io import BytesIO
import json
import os
import time
import traceback
from llm_processing.utility import extract_info_from_text
from llm_processing.transcript6 import Transcript
from llm_processing.llm_interface import ImageProcessor

class ClaudeImageProcessor(ImageProcessor):
    def __init__(self, api_key, prompt_name, prompt_text, model="claude-3-5-sonnet-20240620", modelname="claude-3.5-sonnet"):
        super().__init__(api_key, prompt_name, prompt_text, model, modelname)
        self.client = anthropic.Anthropic(api_key=api_key)

    def set_token_costs_per_mil(self):
        if "3-5-sonnet" in self.model:
            self.input_cost_per_mil = 3.00
            self.output_cost_per_mil = 15.00

    def update_usage(self, message):
        usage = message.usage
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens

    def get_content_from_response(self, response_data):
        text_block = response_data[0].text
        return text_block 

    def extract_json(self, message):
        """Extract JSON from an Anthropic message response including metadata"""
        try:
            # Get the text content and metadata from the message
            content = message.content[0].text
            metadata = {
                "model": message.model,
                "role": message.role,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens
                },
                "id": message.id,
                "type": message.type,
                "stop_reason": message.stop_reason,
                "stop_sequence": message.stop_sequence
            }
            
            # Try to parse content as JSON
            try:
                content_json = json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, try to find JSON within the text
                try:
                    json_start = content.index("{")
                    json_end = content.rindex("}") + 1
                    json_str = content[json_start:json_end]
                    content_json = json.loads(json_str)
                except (ValueError, json.JSONDecodeError):
                    # If no JSON found, use content as is
                    content_json = {"content": content}
            
            # Combine content and metadata
            return {
                "content": content_json,
                "metadata": metadata
            }
                    
        except Exception as e:
            print(f"Error extracting JSON: {str(e)}")
            return {
                "error": str(e), 
                "raw_content": str(message),
                "metadata": metadata if 'metadata' in locals() else None
            }
            
          

    def process_image(self, base64_image, image_ref, index):
        start_time = time.time()
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2500,
                temperature=0,
                system=(
                    "You are an assistant that has a job to extract text from "
                    "an image and parse it out. Only include the text that is "
                    "relevant to the image. Do not Hallucinate"
                ),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt_text},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image,
                                },
                            },
                        ],
                    }
                ],
            )
            end_time = time.time()
            elapsed_time = (end_time - start_time) / 60
            response_data = self.extract_json(message)
            self.save_raw_response(response_data, image_ref)
            self.update_usage(message)
            transcript_processing_data = self.get_transcript_processing_data(elapsed_time)
            if not message.content or not message.content[0].text:
                error_message = f"Error processing image {index + 1} image '{image_ref}': {response_data}"
                return error_message, transcript_processing_data 
            content = self.get_content_from_response(message.content)
            return content, transcript_processing_data
        except requests.exceptions.RequestException as e:
            error_message = (
                f"Error processing image {index + 1} from image '{image_ref}': {str(e)}"
            )
            print(f"ERROR: {error_message}")
            return error_message, None

    def get_image_content_dict(self, image):
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64_image,
            },
        }                 

    def chat(self, prompt_text, image=None):
        print(f"chatting: {prompt_text = }")
        messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text
                        }
                    ]
                }
            ]
        if image:
            messages[0]["content"].append(self.get_image_content_dict(image))
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2500,
            temperature=0,
            system="You are an assistant that has a job to answer questions about an herbarium specimen label. A picture of the label may or may not be provided",
            messages=messages
        )
        response_data = message.content
        print(f"{response_data = }")
        self.update_usage(message)
        return response_data[0].text, self.get_token_costs()
            
