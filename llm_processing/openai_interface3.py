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
from llm_processing.transcript5 import Transcript
from llm_processing.llm_interface import ImageProcessor

class GPTImageProcessor(ImageProcessor):

    def __init__(self, api_key, prompt_name, prompt_text, model="gpt-4o", modelname="gpt-4o"):
        super().__init__(api_key, prompt_name, prompt_text, model, modelname)
        
    def set_token_costs_per_mil(self):
        if "gpt-4o" in self.model:
            self.input_cost_per_mil = 2.50
            self.output_cost_per_mil = 10.00

    def process_image(self, base64_image, image_ref, index, old_version_name):
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
            if "choices" not in response_data:
                error_message = f"Error processing image {index + 1} image '{image_ref}':\n {response_data}"
                return None, error_message, None, image_ref      
            output = self.format_response(f"Image {index + 1}", response_data, image_ref)
            self.update_usage(response_data)
            transcription_dict = extract_info_from_text(output)
            transcript_obj = Transcript(image_ref, self.prompt_name, model=self.modelname)
            end_time = time.time()
            elapsed_time = end_time - start_time
            transcript_processing_data = self.get_transcript_processing_data(elapsed_time)
            try:
                version_name = transcript_obj.create_version(created_by=self.modelname, content=transcription_dict, costs=transcript_processing_data, is_ai_generated=True, old_version_name=old_version_name, editing = {}, new_notes = {})
            except Exception as e:
                trace = traceback.format_exc()
                error_message = (
                    f"Error processing image {index + 1} '{image_ref}': {str(e)}\n{trace}"
                )
                print(f"ERROR: {error_message}")
                f"{error_message}\n{transcription_dict}", None   
            return transcript_obj, version_name
        except requests.exceptions.RequestException as e:
            error_message = (
                f"Error processing local image {index + 1} image '{image_ref}':\n {str(e)}"
            )
            print(f"ERROR: {error_message}")
            return error_message, None           

    def format_response(self, image_name, response_data, image_ref):
        content = response_data["choices"][0].get("message", {}).get("content", "")
        lines = content.split("\n")
        formatted_result = f"{image_name}\n"
        formatted_result += f"image ref: {image_ref}\n\n"
        formatted_result += "\n".join(lines)
        return formatted_result

           