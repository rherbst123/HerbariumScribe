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
from llm_processing.compare2 import TranscriptComparer
from llm_processing.utility import get_fieldnames_from_prompt
from llm_processing.utility import get_image_from_url


class Transcript:
    def __init__(self, image_filename: str, prompt_name: str):
        self.transcription_folder = "output"
        self.ensure_directory_exists(self.transcription_folder)
        self.images_folder = "temp_images"
        self.ensure_directory_exists(self.images_folder)
        self.image_ref = self.get_image_ref(image_filename)
        self.versions =  self.load_versions()
        self.image_source = self.ensure_image_saved(image_filename)
        self.time_started = self.get_timestamp()
        self.prompt_name = prompt_name or self.get_prompt_name_from_base()
        prompt_text = self.get_contents_from_txt("prompts/" + self.prompt_name)
        self.content_fieldnames = get_fieldnames_from_prompt(prompt_text)

    def add_new_notes(self, new_notes):
        for fieldname in new_notes:
            self.versions["notes"][-1][fieldname] = new_notes[fieldname]
            self.versions["content"][-1][fieldname]["notes"] = new_notes[fieldname]    
    
    def commit_version(self, new_notes={}):
        self.finalize_version(new_notes)
        self.save_to_json(self.versions)

    def create_transcription_from_ai(self, content_dict_without_notes, modelname, costs, old_version_name="base", is_ai_generated=True):
        version_name = self.get_version_name(modelname)
        self.intialize_new_version(version_name)
        content_dict = self.fill_out_content_dict(content_dict_without_notes)
        self.versions["content"][-1] = content_dict
        generation_info_dict = self.fill_out_generation_info_dict(new_version_name=version_name, old_version_name=old_version_name, created_by=modelname, is_ai_generated=is_ai_generated)
        self.versions["generation info"][-1] = generation_info_dict
        self.versions["costs"][-1] = costs
        self.commit_version()
        return version_name

    def create_new_version_for_user(self, created_by):
        if self.is_same_user(created_by):
            return self.versions["generation info"][-1]["version name"]
        content_to_be_copied_over = self.versions["content"][-1]
        old_version_name = self.versions["generation info"][-1]["version name"]
        new_version_name = self.get_version_name(created_by)
        self.intialize_new_version(new_version_name)
        self.versions["content"][-1] = copy.deepcopy(content_to_be_copied_over)
        self.versions["generation info"][-1] = self.fill_out_generation_info_dict(new_version_name, old_version_name, created_by, is_ai_generated=False)
        return new_version_name
    
    def ensure_directory_exists(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    def ensure_image_saved(self, image_filename):
        print(f"{image_filename = }")
        image_is_saved = self.is_in_images_folder(self.image_ref)
        print(f"{image_is_saved = }")
        image_source = image_filename if not self.versions else self.versions["generation info"][0]["image source"]
        if not image_is_saved and "http" in image_source:
            print(f"downloading image: {image_source = }")
            image = get_image_from_url(image_source)
            image.save(f"{self.images_folder}/{self.image_ref}")
        return image_source            

    def file_exists(self, filename):
        return os.path.exists(filename)         

    def fill_out_generation_info_dict(self, new_version_name, old_version_name, created_by, is_ai_generated):
        time_created = self.get_timestamp()
        return self.get_generation_info_dict(created_by, new_version_name, old_version_name, time_created, is_ai_generated)

    def fill_out_content_dict(self, content_dict_without_notes):
        return {fieldname: {"value": value, "notes": "", "new notes": ""} for fieldname, value in content_dict_without_notes.items()}                  

    def finalize_version(self, new_notes):
        self.tally_overall_costs()
        self.versions["comparisons"] = self.get_comparisons_dicts()
        self.add_new_notes(new_notes) 

    def get_blank_content_dict(self):
        return {key: {"value": "", "notes": ""} for key in self.content_fieldnames}                   
    
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

    def get_blank_generation_info_dict(self):
        return {"version name": "", 
                "image ref": "", 
                "image source": "", 
                "created by": "", 
                "time created": "", 
                "is ai generated": "", 
                "prompt name": "", 
                "old version name": "", 
                "created by": ""
                } 

    def get_blank_notes_dict(self):
        return {fieldname: "" for fieldname in self.content_fieldnames}                          

    def get_comparisons_dicts(self):
        old_version_name = self.versions["generation info"][-1]["old version name"]
        if old_version_name == "base" or len(self.versions["generation info"]) < 2:
            return {}
        comparer = TranscriptComparer(self)  
        return comparer.compare_all_versions()

    def get_contents_from_txt(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()         

    def get_field_validation_rating(self, fieldname):
        if self.versions["generation info"][-1]["old version name"] == "base":
            return 0
        if "comparisons" not in self.versions or not self.versions["comparisons"]:
            return 0
        comparison = self.versions["comparisons"][-1]
        if not comparison or fieldname not in comparison or not math.floor(comparison[fieldname]):
            return 0
        if "alignment type" not in comparison:
            return 0    
        created_by_types = comparison["alignment type"]
        return 1 if created_by_types==["model", "model"] else 2 if "model" in created_by_types else 3
                                      #modelname, version_name, prior_version_name, transcript_obj.get_timestamp(), is_ai_generated=True)
    def get_generation_info_dict(self, created_by, new_version_name, old_version_name, time_created, is_ai_generated):
        created_by_type = "model" if is_ai_generated else "user"
        d = {"image ref": self.image_ref, "image source": self.image_source, "created by": created_by, "time created": time_created, "is ai generated": is_ai_generated, "prompt name": self.prompt_name, "old version name": old_version_name, "created by type": created_by_type}    
        return {"version name": new_version_name} | d

    def get_image_ref(self, image_filename):
        image_name = image_filename.split("/")[-1]
        return image_name
        
    def get_legal_json_filename(self, image_name):
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", image_name, flags=re.IGNORECASE)
        directory = f"{self.transcription_folder}/versions"
        self.ensure_directory_exists(directory)
        filename = f"{directory}/{ref}-versions.json" 
        return filename   

    def get_models_used(self):
        models = list(set(generation_info["created by"] for generation_info in self.versions["generation info"] if generation_info["is ai generated"]))     
        return models

    def get_prompt_name_from_base(self):
        return self.versions["generation info"][0]["prompt name"]

    def get_timestamp(self):
        return time.strftime("%Y-%m-%d-%H%M")

    def get_version_name(self, created_by):
        return f"{created_by}-{self.time_started}"                 

    def initialize_versions(self):
        d = {
            "version name": [],
            "content": [],
            "costs":  [],
            "notes":  [],
            "editing": [],
            "generation info": [],
            "comparisons": []
            }
        self.versions = d

    def intialize_new_version(self, version_name):
        self.versions["version name"].append(version_name)
        if self.versions["content"]:
            content_to_edit = self.versions["content"][-1]
            self.versions["content"].append({"version name": version_name} | content_to_edit)
        else:
            self.versions["content"].append({"version name": version_name} | self.get_blank_content_dict())
        self.versions["costs"].append({"version name": version_name} | self.get_blank_costs_dict())
        self.versions["notes"].append({"version name": version_name} | self.get_blank_notes_dict())
        self.versions["editing"].append({"version name": version_name} | self.get_blank_editing_dict())
        self.versions["generation info"].append({"version name": version_name} | self.get_blank_generation_info_dict()) 

    def is_in_images_folder(self, image_ref):
        return os.path.exists(f"{self.images_folder}/{image_ref}")        

    def is_same_user(self, created_by):
        return self.versions["generation info"] and self.versions["generation info"][-1]["created by"] == created_by

    def load_versions(self):
        filename = self.get_legal_json_filename(self.image_ref)
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {} 

    def save_to_json(self, content):
        filename = self.get_legal_json_filename(self.image_ref)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)           

    def tally_overall_costs(self):
        costs_list = ["input tokens", "output tokens", "input cost $", "output cost $", "time to create/edit (mins)"]
        overall_costs_dict = {f"overall {cost}": 0 for cost in costs_list}
        for cost in costs_list:
            for cost_history_dict in self.versions["costs"]:
                overall_costs_dict[f"overall {cost}"] += cost_history_dict[cost]
        for overall_cost_name, overall_cost in overall_costs_dict.items():
            self.versions["costs"][-1][overall_cost_name] = overall_cost         
            

    


if __name__ == "__main__":
    ref = "https://fm-digital-assets.fieldmuseum.org/2491/485/C0268502F_p.jpg" 
       
                 

