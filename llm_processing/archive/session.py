import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

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
from llm_processing.transcript5 import Transcript
from llm_processing.compare2 import TranscriptComparer
#from llm_processing.utility import extract_info_from_text
from llm_processing import utility
from llm_processing.llm_manager4 import ProcessorManager
import time

class Session:
    def __init__(self, user_name=""):
        self.user_name = user_name
        self.session_start_time = self.get_timestamp()
        self.overall_session_time = 0
        self.name = ""
        self.transcript_objs = []
        self.content_option = "content"
        self.current_output_dict = {}
        self.current_transcript_idx = 0
        self.fieldnames = []
        self.field_idx = 0
        self.current_transcript_obj = None
        self.processed_images = []
        self.image_refs = []
        self.input_dict = {"api_key_dict": {}, "selected_llms": [], "selected_images_info": [], "images_info_type": ""}
        self.jobs_dict = self.get_blank_jobs_dict()
        self.final_output = ""
        self.editing_data = []
        self.transcription_folder = "output"
        self.ensure_directory_exists(self.transcription_folder)
        self.temp_images_folder = "temp_images"
        self.ensure_directory_exists(self.temp_images_folder)

    def append_processed_elements(self, msg, image, transcript_obj, image_ref):
                                    #   msg, image, transcript_obj, version_name, image_ref
        self.processed_images.append(image)
        self.transcript_objs.append(transcript_obj)
        self.image_refs.append(image_ref)
        output_dict = transcript_obj.versions[0]["content"]
        for fieldname in output_dict:
            output_dict[fieldname]["new notes"] = ""
        self.final_output += image_ref + "\n" + self.dict_to_text(output_dict) + "\n" + ("=" * 50) + "\n"
        editing_data = {"costs": self.get_blank_costs_dict(), "editing": self.get_blank_editing_dict()}
        self.editing_data.append(editing_data)
        msg["editor_enabled"] = True
        return msg

    def dict_to_text(self, d):
        return "\n".join([f"{k}: {v['value']}" for k, v in d.items()]) + 8*"\n"
        
    def dict_to_text_with_rating(self, d):
        return "\n".join([f"{self.get_validation_rating_with_emoji(k)} {k}: {v['value']}" for k, v in d.items()]) + 8*"\n" 

    def end_transcript_editing_time(self):
        elapsed_time = time.time() - time.mktime(time.strptime(self.editing_data[self.current_transcript_idx]["editing"]["time started"], "%Y-%m-%d-%H%M-%S"))
        # Convert seconds to minutes
        elapsed_time = elapsed_time / 60
        self.editing_data[self.current_transcript_idx]["editing"]["time editing"] += elapsed_time
        self.editing_data[self.current_transcript_idx]["costs"]["time to create/edit (mins)"] += elapsed_time
        self.editing_data[self.current_transcript_idx]["editing"]["time started"] = ""
    

    def ensure_directory_exists(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)     

    def get_blank_costs_dict(self):
            return {
                "input tokens": 0,
                "output tokens": 0,
                "input cost $": 0,
                "output cost $": 0,
                "time to create/edit (mins)": 0
            }

    def get_blank_editing_dict(self):
        return {"time started": "", "time editing": 0, "chats": ""} 

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
        }     
        
    def get_combined_output_as_text(self):
        if not self.transcript_objs:
            return "No output to display"
        output = ""
        header = f"Transcription: {len(self.transcript_objs)} images\n\n"
        for image, transcript_obj, image_ref in zip(self.processed_images, self.transcript_objs, self.image_refs):
            prompt_used = transcript_obj.prompt_name
            models_used = ", ".join(transcript_obj.models)
            output_dict = transcript_obj.versions[0]["content"]
            values = "\n".join([f"{fieldname}: {v['value']}" for fieldname, v in output_dict.items()])
            output += f'{image_ref}\nprompt used: {prompt_used}\nmodel(s) used: {models_used}\n\n{values}\n\n{"=" * 50}\n\n'
        return header + "\n" + output 

    def get_content_options(self):
        if self.current_transcript_obj:
            options = [k for k in self.current_transcript_obj.versions[0].keys() if k != "version name"]
            return [o if o != "content" else "transcript" for o in options ]
        else:
            return ["transcript"]

    def get_data_for_table(self, data_name) -> list[dict]:
        return self.current_transcript_obj.versions[0][data_name]        

    def get_image_from_temp_folder(self, image_ref):
        image = Image.open(f"{self.temp_images_folder}/{image_ref}")
        return image                                 

    def get_legal_json_filename(self, image_ref):
        ref = re.sub(r"[\/]", "#", image_ref)
        ref = re.sub(r"[:]", "$", ref)
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
        directory = f"{self.transcription_folder}/transcripts"
        self.ensure_directory_exists(directory)
        filename = f"{directory}/{ref}-transcript.json" 
        return filename       
    
    def get_local_images(self, images_info, msg):
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
                    
                images_to_process.append((base64_image, image_name))
                
            except Exception as e:
                msg["errors"].append(f"Could not open {uploaded_file}: {e}") 
        return images_to_process, msg

    def get_images_from_url(self, images_info, msg):
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
                    
                images_to_process.append((base64_image, image_name))
                
            except Exception as e:
                msg["errors"].append(f"Could not open {url}: {e}") 
        return images_to_process, msg
        

    def get_output_as_text_with_rating(self):
        return self.dict_to_text_with_rating(self.current_output_dict)

    def get_session_filename(self):
        return f"{self.user_name}-{self.get_timestamp()}-session.txt"    

    def get_session_files_list(self):
        session_files = [f for f in os.listdir(f"{self.transcription_folder}/sessions") if f.endswith(".json")]
        sorted_session_files = self.sort_filenames_by_timestamp(session_files)
        return sorted_session_files

    def get_timestamp(self):
        return  time.strftime("%Y-%m-%d-%H%M-%S")

    def get_validation_rating_with_emoji(self, fieldname):
        rating = self.current_transcript_obj.get_field_validation_rating(fieldname)
        if rating:
            return rating*"👍"
        return "🥺" 

    def go_next_image(self):
        if self.transcript_objs:
            if self.current_transcript_idx < len(self.transcript_objs) - 1:
                self.current_transcript_idx += 1
            else:
                self.current_transcript_idx = 0
            self.load_current_transcript_obj()
            
    def go_previous_image(self):
        if self.transcript_objs:
            if self.current_transcript_idx > 0:
                self.current_transcript_idx -= 1
            else:
                self.current_transcript_idx = len(self.transcript_objs) - 1
            self.load_current_transcript_obj()

    def go_to_next_field(self):
        if self.field_idx == len(self.fieldnames) - 1:
            self.field_idx = 0
        else:
            self.field_idx += 1
        
    def go_to_previous_field(self):
        if self.field_idx == 0:
            self.field_idx = len(self.fieldnames) - 1
        else:
            self.field_idx -= 1      

    def initialize_transcript_output(self):
        if self.current_transcript_obj and self.editing_data[self.current_transcript_idx]["editing"]["time started"]:
            self.end_transcript_editing_time()
        self.final_output = self.get_combined_output_as_text()            
        self.current_transcript_idx = 0
        self.field_idx = 0
        self.content_option = "content"
        self.load_current_transcript_obj()
         
    def load_current_transcript_obj(self):
        self.current_transcript_obj = self.transcript_objs[self.current_transcript_idx]
        self.current_output_dict = self.current_transcript_obj.versions[0]["content"]
        self.fieldnames = [k for k in self.current_output_dict.keys()]
        self.current_fieldname = self.fieldnames[self.field_idx]
        self.current_fieldvalue = self.current_output_dict[self.current_fieldname]["value"]
        self.start_transcript_editing_time()             
        
    def load_jobs(self, jobs_dict):
        for job_name, job in jobs_dict.items():
            self.jobs_dict[job_name] = job     
    
    def process_images(self, msg={}):
        msg["errors"] = []
        selected_llms = self.input_dict["selected_llms"]
        selected_prompt_name = self.input_dict["selected_prompt_filename"]
        prompt_text = self.input_dict["prompt_text"]
        selected_images_info = self.input_dict["selected_images_info"]
        images_info_type = self.input_dict["images_info_type"]
        api_key_dict = self.input_dict["api_key_dict"]
        self.current_image_index = 0
        self.final_output = ""
        images_to_process, msg = self.get_local_images(selected_images_info, msg) if images_info_type=="local_images" else self.get_images_from_url(selected_images_info, msg)   
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
        self.load_jobs(jobs_dict)
        msg = self.process_jobs(msg)
        return msg

    def process_jobs(self, msg):
        msg["status"] = []
        jobs = self.jobs_dict
        processor_manager = ProcessorManager(jobs["api_key_dict"], jobs["selected_llms"], jobs["selected_prompt_name"], jobs["prompt_text"])
        copy_images_to_process = jobs["to_process"].copy()
        for idx, image_to_process in enumerate(copy_images_to_process):
            jobs["to_process"].remove(image_to_process)
            jobs["in_process"].append(image_to_process)
            image, transcript_obj, version_name, image_ref = processor_manager.process_one_image(idx, image_to_process)
            if type(transcript_obj) != Transcript:
                msg["pause_button_enabled"] = True
                msg["status"].append(transcript_obj)
                jobs["failed"].append(image_to_process)
                return msg
            else:
                msg["status"].append(f"Successfully processed {image_ref}\n")
                jobs["processed"].append([image_to_process, image_ref])
            msg = self.append_processed_elements(msg, image, transcript_obj, image_ref)
            output_dict = transcript_obj.versions[0]["content"]
            editing_data = {"costs": self.get_blank_costs_dict(), "editing": self.get_blank_editing_dict()}
            self.editing_data.append(editing_data)
        if self.processed_images:
            msg["pause_button_enabled"] = False
            msg["success"] = "Images processed successfully!"
        else:
            msg["warning"] = "No images or errors occurred. Check logs or outputs."
        return msg

    def recreate_transcript_obj(self, transcript_dict):
        image_ref = transcript_dict[0]["generation info"][0]["image ref"]
        prompt_name = transcript_dict[0]["generation info"][0]["prompt name"]
        transcript_obj = Transcript(image_ref, prompt_name)
        #### temporary fix for older transcripts that have url as image_ref
        image_name = transcript_obj.image_ref
        transcript_obj.versions = transcript_dict
        self.transcript_objs.append(transcript_obj)
        self.image_refs.append(image_name)
        image = self.get_image_from_temp_folder(image_name)
        self.processed_images.append(image)
        output_dict = transcript_obj.versions[0]["content"]
        for fieldname in output_dict:
            output_dict[fieldname]["new notes"] = ""
        self.final_output += image_ref + "\n" + self.dict_to_text(output_dict) + "\n" + ("=" * 50) + "\n"
        editing_data = {"costs": self.get_blank_costs_dict(), "editing": self.get_blank_editing_dict()}
        self.editing_data.append(editing_data)    
    
    def re_edit_saved_versions(self, msg, selected_reedit_files):
        msg["errors"] = []
        self.save_edits_to_json()
        self.transcript_objs = []
        try:
            for selected_file in selected_reedit_files:
                with open(os.path.join(f"{self.transcription_folder}/versions", selected_file), "r", encoding="utf-8") as rf:
                    transcript_dict = json.load(rf)
                    self.recreate_transcript_obj(transcript_dict)
        except Exception as e:
            print(f"Error loading file: {str(e)}")
            msg["errors"].append(f"Error loading file: {str(e)}")
        self.initialize_transcript_output()          
        msg["reedit_mode"] = False
        return msg

    def re_edit_session(self, msg, selected_session_file):
        msg["errors"] = []
        self.save_edits_to_json()
        self.transcript_objs = []
        try:
            with open(os.path.join(f"{self.transcription_folder}/sessions", selected_session_file), "r", encoding="utf-8") as rf:
                session_dict = json.load(rf)
                for image_ref, transcript_dict in session_dict.items():
                    self.recreate_transcript_obj(transcript_dict)
        except Exception as e:
            print(f"Error loading file: {str(e)}")
            msg["errors"].append(f"Error loading file: {str(e)}")
        self.initialize_transcript_output()          
        msg["reedit_mode"] = False
        return msg
    
    def reset_inputs(self):
        self.input_dict = {"api_key_dict": {}, "selected_llms": [], "selected_images_info": [], "images_info_type": ""}

    def resume_jobs(self, try_failed_jobs=False):
        msg = {}
        if try_failed_jobs:
            failed_jobs = []
            for job in self.jobs_dict["failed"]:
                if job not in failed_jobs:
                    failed_jobs.append(job)
            self.jobs_dict["to_process"] = failed_jobs + self.jobs_dict["to_process"]
        msg = process_jobs(msg)

    def save_edits_as_text(self):
        self.final_output = self.get_combined_output_as_text() 
   
    def save_edits_to_json(self):
        session_output_dict = {}
        for transcript_obj, image_ref, editing_data in zip(self.transcript_objs, self.image_refs, self.editing_data):
            old_version_name = transcript_obj.versions[0]["generation info"][0]["version name"]
            costs = editing_data["costs"]
            editing = editing_data["editing"]
            output_dict = transcript_obj.versions[0]["content"]
            self.save_to_json(output_dict, image_ref)
            transcript_obj.create_version(created_by=self.user_name, content=output_dict, costs=costs, is_ai_generated=False, old_version_name=old_version_name, editing=editing)
            session_output_dict[image_ref] = transcript_obj.versions
        if session_output_dict:
            directory = f"{self.transcription_folder}/sessions"
            self.ensure_directory_exists(directory)
            session_filename = f"{directory}/{self.user_name}-{self.get_timestamp()}-session.json"
            with open(session_filename, 'w', encoding='utf-8') as f:
                json.dump(session_output_dict, f, ensure_ascii=False, indent=4)    

    def save_table_edits(self, edited_elements, current_output_dict):
        for row_number, columns in edited_elements.items():
            for header, val in columns.items():
                self.current_output_dict[self.fieldnames[row_number]][header] = val      

    def save_to_json(self, content, image_ref):
        filename = self.get_legal_json_filename(image_ref)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)

    def set_current_transcript_obj(self):
        self.field_idx = 0
        self.load_current_transcript_obj()
        
    def sort_filenames_by_timestamp(self, filenames):
        timestamp_pattern = r"(\d{4}-\d{2}-\d{2}-\d{4}-\d{2})"
        return sorted(filenames, key=lambda x: re.search(timestamp_pattern, x).group(1), reverse=True) 

    def start_transcript_editing_time(self):
        self.editing_data[self.current_transcript_idx]["editing"]["time started"] = self.get_timestamp()     

    def update_costs(new_costs: dict):
            old_costs = self.editing_data[self.current_transcript_idx]["costs"]
            for cost_name, val in new_costs.items():
                old_costs[cost_name] += val

    def update_editing(new_editing: dict):
            old_editing = self.editing_data[self.current_transcript_idx]["editing"]
            for editing_name, val in new_editing.items():
                old_editing[editing_name] = val 

    def update_fieldvalue(self, fieldvalue):
        self.current_output_dict[self.current_fieldname]["value"] = fieldvalue             

    def update_text_output(self, current_output_as_text):
        output_dict = utility.extract_info_from_text(current_output_as_text)
        for fieldname, fieldvalue in output_dict.items():
            self.current_output_dict[fieldname]["value"] = fieldvalue       