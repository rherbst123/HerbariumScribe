import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import requests
from PIL import Image
from io import BytesIO
import re
import csv
import json
import time
import math
import copy
from transcript5 import Transcript
from llm_processing.compare2 import TranscriptComparer

class Session:
    def __init__(self, user_name=""):
        self.user_name = user_name
        self.session_start_time = self.get_timestamp()
        self.overall_session_time = 0
        self.name = ""
        self.transcript_objs = []
        self.current_output_dict = {}
        self.current_transcript_idx = 0
        self.current_transcript_obj = None
        self.processed_images = []
        self.image_refs = []
        self.input_dict = {}
        self.final_output = ""
        self.editing_data = []
        self.transcription_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    def append_processed_elements(self, msg, image, transcript_obj, image_ref):
        self.processed_images.append(image)
        self.transcript_objs.append(transcript_obj)
        self.image_refs.append(image_ref)
        output_dict = transcript_obj.versions[0]["content"]
        for fieldname in output_dict:
            output_dict[fieldname]["new notes"] = ""
        self.final_output += image_ref + "\n" + dict_to_text(output_dict) + "\n" + ("=" * 50) + "\n"
        editing_data = {"costs": self.get_blank_costs_dict(), "editing": self.get_blank_editing_dict()}
        self.editing_data.append(editing_data)
        msg["editor_enabled"] = True
        return msg

    
    def dict_to_text(self, d):
        return "\n".join([f"{k}: {v['value']}" for k, v in d.items()]) + 8*"\n"
        
    def dict_to_text_with_rating(self, d):
        return "\n".join([f"{get_validation_rating_with_emoji(k)} {k}: {v['value']}" for k, v in d.items()]) + 8*"\n" 

        
    def get_blank_costs_dict(self):
            return {
                "input tokens": 0,
                "output tokens": 0,
                "input cost $": 0,
                "output cost $": 0
            }

    def get_blank_editing_dict(self):
        return {"time started": 0, "time editing": 0, "chats": ""}  

        
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

    def get_legal_json_filename(self, image_ref):
        ref = re.sub(r"[\/]", "#", image_ref)
        ref = re.sub(r"[:]", "$", ref)
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
        filename = f"{self.transcription_folder}/transcripts/{ref}-transcript.json" 
        return filename 

    def get_option_dict_from_version_in_processed_outputs(self):
        return self.current_transcript_obj.versions[0][self.content_option]             
    
    def get_timestamp(self):
        return  time.strftime("%Y-%m-%d-%H%M-%S")

    def initialize_transcript_outputs(self):
        self.final_output = self.get_combined_output_as_text()            
        self.current_transcript_idx = 0
        self.current_transcript_obj = self.transcript_objs[self.current_transcript_idx]
        self.current_output_dict = get_option_dict_from_version_in_processed_outputs()
        self.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
        self.field_idx = 0
        self.current_fieldname = self.fieldnames[self.field_idx]
        self.current_fieldvalue = self.current_output_dict[self.current_fieldname]["value"]
        self.content_option = ["content"]          
        
    def load_jobs(self, jobs_dict):
        for job_name, job in jobs_dict.items():
            self.job_dict[job_name] = job     
    
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
        images_to_process = []
        if images_info_type == "local_images":
            local_image_files = selected_images_info
            for uploaded_file in local_image_files:
                try:
                    image = Image.open(uploaded_file)
                    images_to_process.append((image, uploaded_file))
                except Exception as e:
                    msg["errors"].append(f"Could not open {uploaded_file}: {e}")
        else:
            images_to_process = selected_images_info           
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

    def process_jobs(self, msg):
        msg["status"] = []
        jobs = self.job_dict
        processor_manager = ProcessorManager(jobs["api_key_dict"], jobs["selected_llms"], jobs["selected_prompt_name"], jobs["prompt_text"])
        copy_images_to_process = jobs["to_process"].copy()
        for idx, image_to_process in enumerate(copy_images_to_process):
            jobs["to_process"].remove(image_to_process)
            jobs["in_process"].append(image_to_process)
            image, transcript_obj, version_name, image_ref = processor_manager.process_one_image(idx, image_to_process)
            if type(transcript_obj) != Transcript:
                msg["pause_button_enabled"] = True
                msg["status"] = transcript_obj
                jobs["failed"].append(image_to_process)
                return msg
            else:
                msg["status"].append(f"Successfully processed {image_ref}\n")
                jobs["processed"].append([image_to_process, image_ref])
            msg = append_processed_elements(msg, image, transcript_obj, version_name, image_ref)
            output_dict = transcript_obj.versions[0]["content"]
            editing_data = {"costs": get_blank_costs_dict(), "editing": get_blank_editing_dict()}
            self.editing_data.append(editing_data)
        if self.processed_images:
            msg["pause_button_enabled"] = False
            msg["success"] = "Images processed successfully!"
        else:
            msg["warning"] = "No images or errors occurred. Check logs or outputs."
        return msg

        
    def re_edit_session(self, msg, selected_session_file):
        msg["errors"] = []
        save_edits_to_json()
        try:
            with open(os.path.join(f"{TRANCRIPTION_FOLDER}/sessions", selected_session_file), "r", encoding="utf-8") as rf:
                session_dict = json.load(rf)
                for image_ref, transcript_dict in session_dict.items():
                    recreate_transcript_obj(transcript_dict)
        except Exception as e:
                msg["errors"].append(f"Error loading file: {str(e)}")
        initialize_transcript_outputs()          
        msg["reedit_mode"] = False
        return msg
    
    def reset_inputs(self):
        self.input_dict = {}

    def resume_jobs(self, try_failed_jobs=False):
        if try_failed_jobs:
            failed_jobs = []
            for job in st.session_state.job_dict["failed"]:
                if job not in failed_jobs:
                    failed_jobs.append(job)
            st.session_state.job_dict["to_process"] = failed_jobs + st.session_state.job_dict["to_process"]
        process_jobs()

            
    def save_edits_to_json(self):
        update_processed_outputs()
        session_output_dict = {}
        for transcript_obj, image_ref, editing_data in zip(self.transcript_objs, self.image_refs, self.editing_data):
            old_version_name = transcript_obj.versions[0]["new version name"]
            #print(f"in save_edits_to_json: {old_version_name = }")
            costs = editing_data["costs"]
            #print(f"in save_edits_to_json: {costs = }")
            editing = editing_data["editing"]
            #print(f"in save_edits_to_json: {editing = }")
            output_dict = transcript_obj.versions[0]["content"]
            #print(f"in save_edits_to_json: {output_dict = }")
            self.save_to_json(output_dict, image_ref)
            transcript.create_version(created_by=self.user_name, content=output_dict, costs=costs, is_ai_generated=False, old_version_name=old_version_name, editing=editing)
            session_output_dict[image_ref] = transcript.versions
        session_filename = f"{self.transcription_folder}/sessions/{self.user_name}-{get_timestamp()}-session.json"
        if session_output_dict:
            with open(session_filename, 'w', encoding='utf-8') as f:
                json.dump(session_output_dict, f, ensure_ascii=False, indent=4)    

    
    def save_to_json(self, content, image_ref):
        filename = get_legal_json_filename(image_ref)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)