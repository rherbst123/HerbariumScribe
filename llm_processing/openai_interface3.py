import openai
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

class GPTImageProcessor(ImageProcessor):

    def __init__(self, api_key, prompt_name, prompt_text, model="gpt-4o", modelname="gpt-4o"):
        super().__init__(api_key, prompt_name, prompt_text, model, modelname)
        
    def set_token_costs_per_mil(self):
        if "gpt-4o" in self.model:
            self.input_cost_per_mil = 2.50
            self.output_cost_per_mil = 10.00

    def process_image(self, base64_image, image_ref, index):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        start_time = time.time()
        try:
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0,
                "seed": 42
            }
            post_resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response_data = post_resp.json()
            self.save_raw_response(response_data, image_ref)
            self.update_usage(response_data)
            end_time = time.time()
            elapsed_time = (end_time - start_time) / 60
            if "choices" not in response_data:
                error_message = f"Error processing image {index + 1} image '{image_ref}':\n {response_data}"
                return error_message, self.get_transcript_processing_data(elapsed_time)      
            content = self.get_content_from_response(response_data)
            return content, self.get_transcript_processing_data(elapsed_time)
        except requests.exceptions.RequestException as e:
            error_message = (
                f"Error processing local image {index + 1} image '{image_ref}':\n {str(e)}"
            )
            print(f"ERROR: {error_message}")
            return error_message, None           

    def get_content_from_response(self, response_data):
        content = response_data["choices"][0].get("message", {}).get("content", "")
        return content

           