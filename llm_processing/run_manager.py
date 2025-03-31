from llm_processing.jobs_runner import JobsRunner
import time
import requests
from PIL import Image
from io import BytesIO
import base64
import re
import csv
import json
import time
import math
import copy

class RunManager:
    def __init__(self, msg, input_dict, user_name):
        self.input_dict = input_dict
        self.msg = msg
        self.user_name = user_name
        self.transcription_folder = "transcription"
        self.temp_images_folder = "temp_images"

    def get_blank_jobs_dict(self):
        return {
            "api_key_dict": {},
            "selected_llms": [],
            "selected_prompt_name": "",
            "prompt_text": "",
            "to_process": [],
            "in_process": [],
            "processed": [],
            "failed": [],
            "transcript_objs": []
        }     
    
    def get_local_images(self, images_info):
        images_to_process = []
        for uploaded_file in images_info:
            try:
                image = Image.open(uploaded_file)
                
                # Create a byte buffer and save image as JPEG
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                image_bytes = buffer.getvalue()
                
                # Convert to base64
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                # Get the name of the uploaded file
                image_name = uploaded_file.name
                
                # Save to temp folder
                with open(f"{self.temp_images_folder}/{image_name}", "wb") as f:
                    image.save(f)
                    
                images_to_process.append((base64_image, image_name, image))
                
            except Exception as e:
                self.msg["errors"].append(f"Could not open {uploaded_file}: {e}") 
        return images_to_process

    def get_images_from_url(self, images_info):
        images_to_process = []
        for url in images_info:
            try:
                response = requests.get(url)
                image = Image.open(BytesIO(response.content))
            
                # Create a byte buffer and save image as JPEG
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                image_bytes = buffer.getvalue()
                
                # Convert to base64
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                # Extract filename from URL or use URL as filename
                image_name = url.split('/')[-1]  # Gets the last part of the URL as filename
                if not any(image_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                    image_name += '.jpg'  # Add extension if missing
                
                # Save to temp folder
                with open(f"{self.temp_images_folder}/{image_name}", "wb") as f:
                    image.save(f)
                    
                images_to_process.append((base64_image, image_name, image))
                
            except Exception as e:
                self.msg["errors"].append(f"Could not open {url}: {e}") 
        return images_to_process
        
    def get_timestamp(self):
        return time.strftime("%Y-%m-%d-%H%M-%S")
    
    def process_images(self):
        self.msg["errors"] = []
        selected_llms = self.input_dict["selected_llms"]
        selected_prompt_name = self.input_dict["selected_prompt_filename"]
        prompt_text = self.input_dict["prompt_text"]
        selected_images_info = self.input_dict["selected_images_info"]
        images_info_type = self.input_dict["images_info_type"]
        api_key_dict = self.input_dict["api_key_dict"]
        self.current_image_index = 0
        self.final_output = ""
        images_to_process = self.get_local_images(selected_images_info) if images_info_type=="local_images" else self.get_images_from_url(selected_images_info)   
        jobs_dict = {
            "api_key_dict": api_key_dict,
            "selected_llms": selected_llms,
            "selected_prompt_name": selected_prompt_name,
            "prompt_text": prompt_text,
            "to_process": images_to_process,
            "in_process": [],
            "processed": [],
            "failed": [],
        }
        self.jobs_runner = JobsRunner(self.msg, self.user_name)
        self.jobs_runner.load_jobs(jobs_dict)
        self.jobs_runner.process_jobs()
        transcript_pages = self.jobs_runner.get_transcript_pages()
        self.jobs_runner.clear_transcript_pages()
        return transcript_pages

    def process_jobs(self):
        self.jobs_runner.process_jobs()

    def reset_inputs(self):
        self.input_dict = {"api_key_dict": {}, "selected_llms": [], "selected_images_info": [], "images_info_type": ""}

    def resume_jobs(self, try_failed_jobs):
        self.jobs_runner.resume_jobs()
        transcript_pages = self.jobs_runner.get_transcript_pages()
        self.jobs_runner.clear_transcript_pages()
        return transcript_objs

    def save_to_json(self, content, image_ref):
        filename = self.get_legal_json_filename(image_ref)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)