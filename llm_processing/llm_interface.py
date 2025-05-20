import time
import json
import os
import re

class ImageProcessor:

    def __init__(self, api_key, prompt_name, prompt_text, model, modelname):
        self.raw_response_folder = "llm_processing/raw_response_data"
        self.ensure_directory_exists(self.raw_response_folder)
        self.api_key = api_key.strip()
        self.prompt_name = prompt_name
        self.prompt_text = prompt_text
        self.model = model
        self.modelname = modelname
        self.input_tokens = 0
        self.output_tokens = 0
        self.set_token_costs_per_mil()
        self.num_processed = 0
        print(f"Initialized ImageProcessor with model: {self.model}")

    def ensure_directory_exists(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)    

    def get_timestamp(self):
        return  time.strftime("%Y-%m-%d-%H%M-%S")
    
    def get_token_costs(self):
        return {
            "input tokens": self.input_tokens,
            "output tokens": self.output_tokens,
            "input cost $": round((self.input_tokens / 1_000_000) * self.input_cost_per_mil, 3),
            "output cost $": round((self.output_tokens / 1_000_000) * self.output_cost_per_mil, 3)
        }         

    def get_transcript_processing_data(self, time_elapsed):
        return {
                "time to create/edit (mins)": time_elapsed,
                } | self.get_token_costs()

    def save_raw_response(self, response_data, image_name):
        model_name_safe = re.sub(r'[-\.: ]', '_', self.model)
        directory = f"{self.raw_response_folder}/{model_name_safe}"
        self.ensure_directory_exists(directory)
        filename = f"{directory}/{image_name}-{self.get_timestamp()}-raw.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, ensure_ascii=False, indent=4)             

    def update_usage(self, response_data):
        if "usage" in response_data:
            usage = response_data["usage"]
            self.input_tokens = int(usage.get("prompt_tokens", 0))
            self.output_tokens = int(usage.get("completion_tokens", 0))                           