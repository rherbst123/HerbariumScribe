import openai
import base64
import requests
from PIL import Image
from io import BytesIO
import json
import os
import time
from llm_interfaces.utility import extract_info_from_text
from llm_interfaces.transcript import Transcript

class GPTImageProcessorThread:
                # (api_key, st.session_state.prompt_text, urls, result_queue)
    def __init__(self, api_key, prompt_name, prompt_text, urls, result_queue):
        self.api_key = api_key
        self.prompt_name = prompt_name
        self.prompt_text = prompt_text
        self.urls = urls
        self.result_queue = result_queue
        self.model = "gpt-4o"
        self.modelname = "gpt-4o"
        self.input_tokens = 0
        self.output_tokens = 0
        self.set_token_costs_per_mil()

    def set_token_costs_per_mil(self):
        if "gpt-4o" in self.model:
            self.input_cost_per_mil = 2.50
            self.output_cost_per_mil = 10.00

    def get_token_costs(self):
        return {
            "input tokens": self.input_tokens,
            "output tokens": self.output_tokens,
            "input cost $": round((self.input_tokens / 1_000_000) * self.input_cost_per_mil, 2),
            "output cost $": round((self.output_tokens / 1_000_000) * self.output_cost_per_mil, 2)
        }         

    def encode_image_to_base64(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def update_usage(self, response_data):
        if "usage" in response_data:
            usage = response_data["usage"]
            self.input_tokens += int(usage.get("prompt_tokens", 0))
            self.output_tokens += int(usage.get("completion_tokens", 0))       

###############

    def process_images(self):
        total_time = time.time()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        for index, url in enumerate(self.urls):
            url = url.strip()
            start_time = time.time()
            try:
                response = requests.get(url)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                buffered = BytesIO()
                image.save(buffered, format="JPEG")
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
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
                output = self.format_response(f"Image {index + 1}", response_data, url)
                self.update_usage(response_data)
                transcription_dict = extract_info_from_text(output)
                transcript_obj = Transcript(url, self.prompt_name)
                end_time = time.time()
                elapsed_time = end_time - start_time
                transcript_processing_data = self.get_transcript_processing_data(elapsed_time)
                version_name = transcript_obj.create_version(created_by=self.modelname, content=transcription_dict, data=transcript_processing_data)
                self.result_queue.put((image, transcript_obj, version_name, url))
            except requests.exceptions.RequestException as e:
                error_message = (
                    f"Error processing image {index + 1} from URL '{url}': {str(e)}"
                )
                print(f"ERROR: {error_message}")
                self.result_queue.put((None, error_message, None, None))
        print("\nAll images processed. Sending completion signal.")
        self.result_queue.put((None, None, None, None))

    def get_transcript_processing_data(self, time_elapsed):
        return {
                "created by": self.modelname,
                "is user": False,
                "time to create/edit": time_elapsed,
                } | self.get_token_costs()       

    def format_response(self, image_name, response_data, url):
        content = response_data["choices"][0].get("message", {}).get("content", "")
        lines = content.split("\n")
        formatted_result = f"{image_name}\n"
        formatted_result += f"URL: {url}\n\n"
        formatted_result += "\n".join(lines)
        return formatted_result

           