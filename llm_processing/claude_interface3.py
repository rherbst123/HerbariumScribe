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
from llm_processing.transcript5 import Transcript
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

    def format_response(self, image_name, response_data, image_ref):
        text_block = response_data[0].text
        lines = text_block.split("\n")
        formatted_result = f"{image_name}\n"
        formatted_result += f"image ref: {image_ref}\n\n"
        formatted_result += "\n".join(lines)
        return formatted_result   

    def process_image(self, base64_image, image_ref, index, old_version_name):
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
            if not message.content or not message.content[0].text:
                error_message = f"Error processing image {index + 1} image '{image_ref}': {response_data}"
                return error_message, None 
            output = self.format_response(f"Image {index + 1}", message.content, image_ref)
            self.update_usage(message)
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
                return f"{error_message}\n{transcription_dict}", None
            return transcript_obj, version_name
        except requests.exceptions.RequestException as e:
            error_message = (
                f"Error processing image {index + 1} from image '{image_ref}': {str(e)}"
            )
            print(f"ERROR: {error_message}")

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
            
