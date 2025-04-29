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
from llm_processing.transcript6 import Transcript
from llm_processing.compare2 import TranscriptComparer
from llm_processing import utility
from llm_processing.volume import Volume
from llm_processing.processing_manager import ProcessingManager
import time

class Session:
    def __init__(self, user_name=""):
        self.user_name = user_name
        self.session_start_time = self.get_timestamp()
        self.overall_session_time = 0
        self.name = f"{self.user_name}-{self.session_start_time}"
        self.msg = {"pause_button_enabled": False, "status": []}
        self.table_type = "page"
        self.table_content_option = "content"
        self.input_dict = {"api_key_dict": {}, "selected_llms": [], "selected_images_info": [], "images_info_type": ""}
        self.volume = None
        self.pages = []
        self.final_output = ""
        self.transcription_folder = "output"
        self.ensure_directory_exists(self.transcription_folder)
        self.temp_images_folder = "temp_images"
        self.ensure_directory_exists(self.temp_images_folder)
        self.processing_manager = None
        self.background_processing = False
    

    def dict_to_text(self, d):
        return "\n".join([f"{k}: {v['value']}" for k, v in d.items()]) + 8*"\n"
        
    def dict_to_text_with_rating(self, d):
        return "\n".join([f"{self.get_validation_rating_with_emoji(k)} {k}: {v['value']}" for k, v in d.items()]) + 8*"\n" 

    def end_transcript_editing_time(self):
        elapsed_time = time.time() - time.mktime(time.strptime(self.volume.current_transcript_obj.versions["editing"][-1]["time started"], "%Y-%m-%d-%H%M-%S"))
        elapsed_time = elapsed_time / 60
        self.volume.current_transcript_obj.versions["editing"][-1]["time editing"] += elapsed_time
        self.volume.current_transcript_obj.versions["costs"][-1]["time to create/edit (mins)"] += elapsed_time
        self.volume.current_transcript_obj.versions["editing"][-1]["time started"] = ""
    
    def ensure_directory_exists(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)  

    def get_combined_output_as_text(self):
        if not self.pages:
            return "No output to display"
        output = ""
        header = f"Transcription: {len(self.pages)} images\n\n"
        for page in self.pages:
            transcript_obj = page["transcript_obj"]
            prompt_used = transcript_obj.prompt_name
            models_used = ", ".join(transcript_obj.get_models_used())
            output_dict = transcript_obj.versions["content"][-1]
            values = "\n".join([f"{fieldname}: {v['value']}" for fieldname, v in output_dict.items()])
            image_ref = page["image_ref"]
            output += f'{image_ref}\nprompt used: {prompt_used}\nmodel(s) used: {models_used}\n\n{values}\n\n{"=" * 50}\n\n'
        return header + "\n" + output 

    def get_table_content_options(self):
        return self.get_transcript_content_options() if self.table_type == "page" else self.get_volume_data_options()  

    def get_transcript_content_options(self):
        if self.volume.current_transcript_obj.versions:
            options = [k for k in self.volume.current_transcript_obj.versions.keys() if k != "version name"]
            return [o if o != "content" else "transcript" for o in options ]
        else:
            return [k for k in self.volume.data.keys()]

    def get_data_for_table(self) -> list[dict]:
        return self.volume.current_transcript_obj.versions[self.table_content_option] if self.table_type=="page" else self.volume.data["costs"]      

    def get_image_from_temp_folder(self, image_ref):
        image = Image.open(f"{self.temp_images_folder}/{image_ref}")
        return image                                 
#
    def get_legal_json_filename(self, image_ref):
        ref = re.sub(r"[\/]", "#", image_ref)
        ref = re.sub(r"[:]", "$", ref)
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
        directory = f"{self.transcription_folder}/transcripts"
        self.ensure_directory_exists(directory)
        filename = f"{directory}/{ref}-transcript.json" 
        return filename       

    def get_output_as_text_with_rating(self):
        return self.dict_to_text_with_rating(self.volume.current_output_dict)

    def get_volume_filename(self):
        return f"{self.volume.name}-volume.txt"

    def get_volume_data_options(self):
        return [k for k in self.volume.data.keys()]        

    def get_volume_files_list(self):
        volume_files = [f for f in os.listdir(f"{self.transcription_folder}/volumes") if f.endswith(".json")]
        sorted_volume_files = self.sort_filenames_by_timestamp(volume_files)
        return sorted_volume_files

    def get_timestamp(self):
        return  time.strftime("%Y-%m-%d-%H%M-%S")

    def get_validation_rating_with_emoji(self, fieldname):
        rating = self.volume.current_transcript_obj.get_field_validation_rating(fieldname)
        if rating:
            return rating*"👍"
        return "🥺" 

    def go_next_image(self):
        if self.pages:
            page_idx = self.volume.current_page_idx
            if page_idx < len(self.pages) - 1:
                self.volume.current_page_idx += 1
            else:
                self.volume.current_page_idx = 0
            self.load_current_transcript_obj()
            
    def go_previous_image(self):
        if self.pages:
            page_idx = self.volume.current_page_idx
            if page_idx > 0:
                self.volume.current_page_idx -= 1
            else:
                self.volume.current_page_idx = len(self.pages) - 1
            self.load_current_transcript_obj()

    def go_to_next_field(self):
        field_idx = self.volume.field_idx
        if field_idx == len(self.volume.fieldnames) - 1:
            self.volume.field_idx = 0
            self.volume.set_current_field()
        else:
            self.volume.field_idx = field_idx + 1
            self.volume.set_current_field()
        
    def go_to_previous_field(self):
        field_idx = self.volume.field_idx
        if field_idx == 0:
            self.volume.field_idx = len(self.volume.fieldnames) - 1
            self.volume.set_current_field()
        else:
            self.volume.field_idx = field_idx - 1
            self.volume.set_current_field()

    def initialize_volume(self, volume_name):
        return Volume(self.msg, volume_name)              

    def initialize_transcript_output(self):
        self.final_output = self.get_combined_output_as_text()
        self.load_current_transcript_obj()
        self.msg["editor_enabled"] = True
         
    def load_current_transcript_obj(self):
        if self.volume.current_page and self.volume.current_transcript_obj and self.volume.current_transcript_obj.versions and self.volume.current_transcript_obj.versions["editing"][-1]["time started"]:
            self.end_transcript_editing_time()
        self.volume.set_current_page()
        self.start_transcript_editing_time()             
   
    def process_initial_batch(self, volume_name, initial_batch_size):
        self.volume = self.initialize_volume(volume_name)
        self.pages = self.volume.pages
        self.processing_manager = ProcessingManager(self.msg, self.input_dict, self.volume, self.user_name)
        try:
            self.processing_manager.process_initial_batch(initial_batch_size)
            print("session process_batch returned")
            print(f"{self.volume.pages = }")
        except Exception as e:
            self.msg["errors"].append(f"Error processing images: {str(e)}")
        self.msg["status"].append(f"Volume {volume_name} created and saved!!!!")      
        
    def recreate_transcript_obj(self, transcript_dict):
        image_name = transcript_dict["generation info"][-1]["image ref"]
        prompt_name = transcript_dict["generation info"][-1]["prompt name"]
        transcript_obj = Transcript(image_name, prompt_name)
        transcript_obj.versions = transcript_dict
        version_name = transcript_obj.create_new_version_for_user(self.user_name)
        image = self.get_image_from_temp_folder(image_name)
        page = {"image_ref": image_name, "transcript_obj": transcript_obj, "image": image, "version_name": version_name}
        self.volume.add_page(page)

    def re_edit_volume(self, selected_volume_file):
        volume_name = selected_volume_file.split("-volume.json")[0]
        self.msg["errors"] = []
        if self.volume:
            pass
            #self.volume.commit_volume()
        self.volume = self.initialize_volume(volume_name)
        self.pages = self.volume.pages
        try:
            with open(os.path.join(f"{self.transcription_folder}/volumes", selected_volume_file), "r", encoding="utf-8") as rf:
                volume_dict = json.load(rf)
                for key, volume_dict in volume_dict.items():
                    if key == "volume data":
                        self.volume.set_data(volume_dict)
                    else:    
                        self.recreate_transcript_obj(volume_dict)
        except Exception as e:
            print(f"Error loading file: {str(e)}")
            self.msg["errors"].append(f"Error loading file: {str(e)}")
        self.initialize_transcript_output()          
        self.msg["reedit_mode"] = False
#    
    def reset_inputs(self):
        self.input_dict = {"api_key_dict": {}, "selected_llms": [], "selected_images_info": [], "images_info_type": ""}
#
    def reset_msg(self):
        print(f"session.reset_msg called")
        self.msg = {"pause_button_enabled": False, "status": []}

    def resume_jobs(self, try_failed_jobs, batch_size=None):
        self.msg["pause_button_enabled"] = False
        self.processing_manager.resume_jobs(try_failed_jobs, batch_size)

    def save_edits_as_text(self):
        self.final_output = self.get_combined_output_as_text() 
   
    def save_edits_to_json(self):
        for page in self.pages:
            transcript_obj = page["transcript_obj"]
            image_ref = page["image_ref"]
            output_dict = transcript_obj.versions["content"][-1]
            self.save_to_json(output_dict, image_ref)
            transcript_obj.commit_version()
        self.volume.commit_volume()   

    def save_table_edits(self, edited_elements={}):
        for row_number, columns in edited_elements.items():
            for header, val in columns.items():
                self.volume.current_output_dict[self.volume.fieldnames[row_number]][header] = val      
#
    def save_to_json(self, content, image_ref):
        filename = self.get_legal_json_filename(image_ref)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)

    def set_current_transcript_obj(self):
        self.volume.field_idx = 0
        self.load_current_transcript_obj()
        
    def sort_filenames_by_timestamp(self, filenames):
        return filenames
        timestamp_pattern = r"(\d{4}-\d{2}-\d{2}-\d{4}-\d{2})"
        return filenames.sort(key=lambda x: re.search(timestamp_pattern, x).group(1), reverse=True)
        return sorted(filenames, key=lambda x: re.search(timestamp_pattern, x).group(1), reverse=True) 

    def start_transcript_editing_time(self):
        self.volume.current_transcript_obj.versions["editing"][-1]["time started"] = self.get_timestamp()     

    def update_fieldvalue(self, fieldvalue):
        fieldname = self.volume.fieldnames[self.volume.field_idx]
        self.volume.current_output_dict[fieldname]["value"] = fieldvalue             

    def update_text_output(self, current_output_as_text):
        output_dict = utility.extract_info_from_text(current_output_as_text)
        for fieldname, fieldvalue in output_dict.items():
            self.volume.current_output_dict[fieldname]["value"] = fieldvalue       