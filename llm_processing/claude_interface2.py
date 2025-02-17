import anthropic
import base64
import requests
from PIL import Image
from io import BytesIO
import json
import os
import time
from llm_processing.utility import extract_info_from_text
from llm_processing.transcript3 import Transcript

class ClaudeImageProcessorThread:
    def __init__(self, api_key, prompt_name, prompt_text):
        self.api_key = api_key.strip()
        self.prompt_name = prompt_name
        self.prompt_text = prompt_text
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20240620"
        self.modelname = "claude-3.5-sonnet"
        self.client = anthropic.Anthropic(api_key=api_key)
        self.input_tokens = 0
        self.output_tokens = 0
        self.set_token_costs_per_mil()
        self.num_processed = 0

    def set_token_costs_per_mil(self):
        if "3-5-sonnet" in self.model:
            self.input_cost_per_mil = 3.00
            self.output_cost_per_mil = 15.00

    def get_token_costs(self):
        return {
            "input tokens": self.input_tokens,
            "output tokens": self.output_tokens,
            "input cost $": round((self.input_tokens / 1_000_000) * self.input_cost_per_mil, 4),
            "output cost $": round((self.output_tokens / 1_000_000) * self.output_cost_per_mil, 4)
        }         

    def encode_image_to_base64(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8') 

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

    def process_image_from_url(self, url, index, old_version_name):
        url = url.strip()
        start_time = time.time()
        try:
            response = requests.get(url)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4096,
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
            output = self.format_response(f"Image {index + 1}", message.content, url)
            self.update_usage(message)
            transcription_dict = extract_info_from_text(output)
            transcript_obj = Transcript(url, self.prompt_name)
            end_time = time.time()
            elapsed_time = end_time - start_time
            transcript_processing_data = self.get_transcript_processing_data(elapsed_time)
            version_name = transcript_obj.create_version(created_by=self.modelname, content=transcription_dict, data=transcript_processing_data, is_user=False, old_version_name=old_version_name)
            self.num_processed += 1
            print(f"claude: {self.num_processed = }")
            return image, transcript_obj, version_name, url

        except requests.exceptions.RequestException as e:
            error_message = (
                f"Error processing image {index + 1} from URL '{url}': {str(e)}"
            )
            print(f"ERROR: {error_message}")
            return None, error_message, None, None
        
    def process_local_image(self, local_image, index, old_version_name):
        image, filename = local_image
        start_time = time.time()
        try:
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
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
            output = self.format_response(f"Image {index + 1}", message.content, filename)
            self.update_usage(message)
            transcription_dict = extract_info_from_text(output)
            transcript_obj = Transcript(filename, self.prompt_name)
            end_time = time.time()
            elapsed_time = end_time - start_time
            transcript_processing_data = self.get_transcript_processing_data(elapsed_time)
            version_name = transcript_obj.create_version(created_by=self.modelname, content=transcription_dict, data=transcript_processing_data, is_user=False, old_version_name=old_version_name)
            self.num_processed += 1
            print(f"claude: {self.num_processed = }")
            return image, transcript_obj, version_name, filename
        except requests.exceptions.RequestException as e:
            error_message = (
                f"Error processing image {index + 1} from local image '{filename}': {str(e)}"
            )
            print(f"ERROR: {error_message}")
            return None, error_message, None, None

    def get_transcript_processing_data(self, time_elapsed):
        return {
                "created by": self.modelname,
                "is user": False,
                "time to create/edit": time_elapsed,
                } | self.get_token_costs()

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
            
