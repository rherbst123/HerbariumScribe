from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import requests
from PIL import Image
from io import BytesIO
import base64
#from llm_processing.llm_manager_testing import LLMManager
from llm_processing.llm_manager4 import LLMManager
from llm_processing.transcript6 import Transcript
from llm_processing.jobs_runner import JobsRunner

class ProcessingManager:
    def __init__(self, msg, input_dict, volume, user_name):
        self.msg = msg
        self.input_dict = input_dict
        self.volume = volume
        self.user_name = user_name    
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.processing_queue = Queue()
        self.processed_results = {}
        self.is_processing = False
        self.transcription_folder = "transcription"
        self.temp_images_folder = "temp_images"
        self.setup_jobs()

    def setup_jobs(self):
        self.msg["errors"] = []
        self.msg["pause_button_enabled"] = False
        self.msg["status"] = []
        self.jobs_dict = self.get_blank_jobs_dict()
        selected_images_info = self.input_dict["selected_images_info"]
        images_info_type = self.input_dict["images_info_type"]
        self.jobs_dict["to_process"] = self.get_local_images(selected_images_info) if images_info_type == "local" else self.get_images_from_url(selected_images_info)
        self.jobs_runner = JobsRunner(self.msg, self.user_name, self.input_dict, self.volume)
        self.jobs_runner.load_jobs(self.jobs_dict)

                          
    def get_local_images(self, images_info):
        images_to_process = []
        for uploaded_file in images_info:
            try:
                image = Image.open(uploaded_file)
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                image_bytes = buffer.getvalue()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                image_name = uploaded_file.name
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
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                image_bytes = buffer.getvalue()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                image_name = url.split('/')[-1]  # Gets the last part of the URL as filename
                if not any(image_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                    image_name += '.jpg'
                with open(f"{self.temp_images_folder}/{image_name}", "wb") as f:
                    image.save(f)
                images_to_process.append((base64_image, url, image))
            except Exception as e:
                self.msg["errors"].append(f"Could not open {url}: {e}") 
        return images_to_process    

    def get_blank_jobs_dict(self):
        return {
            "to_process": [],
            "in_process": [],
            "processed": [],
            "failed": [],
            "transcript_objs": [],
            "pages": []
        }        

    def process_initial_batch(self, batch_size=3):
        self.jobs_runner.process_jobs(batch_size)
        
    def start_background_processing(self):
        self.jobs_runner.process_jobs()

    def resume_jobs(self, try_failed_jobs, batch_size=None):
        self.jobs_runner.resume_jobs(try_failed_jobs, batch_size)    