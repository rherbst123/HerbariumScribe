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


class Transcript:
    def __init__(self, image_ref: str, prompt_name: str, model="", time_started=None):
        self.image_ref, self.image_source = self.get_image_ref(image_ref)
        self.prompt_name = prompt_name
        self.transcription_folder = "output"
        self.ensure_directory_exists(self.transcription_folder)
        self.versions =  self.load_versions()
        self.time_started = time_started or self.get_timestamp()
        self.prompt_name = prompt_name or self.get_prompt_name_from_base()
        self.models = [model] or self.get_models_used()
        self.content_fieldnames = []

    def combine_new_and_old(self, generation_info_dict, new_costs_dict, new_editing_dict, new_notes_dict):
        d = {}
        d["generation info"] = [generation_info_dict] + self.versions[0]["generation info"]
        d["costs"] = [new_costs_dict] + self.versions[0]["costs"]
        d["editing"] = [new_editing_dict] + self.versions[0]["editing"]
        d["notes"] = [new_notes_dict] + self.versions[0]["notes"]
        return d

    #                        created_by=self.modelname, content=transcription_dict, costs=transcript_processing_data, is_ai_generated=True, old_version_name=old_version_name, editing = {})
    def create_version(self, created_by, content, costs, is_ai_generated=True, old_version_name="base", editing = {}):
        new_version_name = self.get_version_name(created_by)  
        if not self.versions:
            self.content_fieldnames = list(content.keys())
            self.initialize_versions(new_version_name)
        generation_info_dict = self.get_generation_info_dict(created_by, new_version_name, old_version_name, self.get_timestamp(), is_ai_generated)
        new_content_dict, new_notes = self.update_content(content, new_version_name, is_ai_generated)
        new_notes_dict = self.update_notes(new_notes, created_by, new_version_name)    
        new_costs_dict = self.update_costs(costs, editing, new_version_name)
        new_editing_dict = {"version name": new_version_name} | editing
        new_version = self.get_new_version(new_version_name, old_version_name, generation_info_dict, new_content_dict, new_costs_dict, new_editing_dict, new_notes_dict)
        if  old_version_name=="base" or self.is_same_user(created_by):
            self.versions[0] = new_version
        else:
            self.versions.insert(0, new_version)
        self.save_to_json(self.versions)
        return new_version_name
    
    def ensure_directory_exists(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory) 

    def get_comparisons_dicts(self, old_version_name):
        print("get_comparisons_dict called")
        if old_version_name == "base":
            return {}
        comparer = TranscriptComparer(self)  
        return comparer.compare_all_versions()          

    def get_costs_list(self):
        return ["input tokens", "output tokens", "input cost $", "output cost $", "time to create/edit (mins)"]                

    def get_field_validation_rating(self, fieldname):
        if self.versions[0]["generation info"][0]["old version name"] == "base":
            return 0
        if not self.versions[0]["comparisons"]:
            print("ERROR: no comparisons found")
            return 0
        comparison = self.versions[0]["comparisons"][0]
        if not comparison or fieldname not in comparison or not math.floor(comparison[fieldname]):
            return 0
        if "alignment type" not in comparison:
            return 0    
        created_by_types = comparison["alignment type"]
        return 1 if created_by_types==["model", "model"] else 2 if "model" in created_by_types else 3
    
    def get_generation_info_dict(self, created_by, new_version_name, old_version_name, time_created, is_ai_generated):
        created_by_type = "model" if is_ai_generated else "user"
        d = {"image ref": self.image_ref, "image source": self.image_source, "created by": created_by, "time created": time_created, "is ai generated": is_ai_generated, "prompt name": self.prompt_name, "old version name": old_version_name, "created by type": created_by_type}    
        return {"version name": new_version_name} | d

    def get_image_ref(self, image_filename):
        try:        
            mtch = re.search(r"(.+[/\\])(.+(jpg)|(jpeg)|(png))", image_filename)
            image_source = mtch.group(1)
            image_name = mtch.group(2)
        except:
            image_name = image_filename
            image_source = "undefined"
            print(f"ERROR: current regex does not capture image_ref: {image_filename}")
        return image_name, image_source     

    def get_legal_json_filename(self):
        ref = re.sub(r"[\/]", "#", self.image_ref)
        ref = re.sub(r"[:]", "$", ref)
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
        directory = f"{self.transcription_folder}/versions"
        self.ensure_directory_exists(directory)
        filename = f"{directory}/{ref}-versions.json" 
        return filename   

    def get_models_used(self):
        models = list(set([v["generation info"][0]["created by"] for v in self.versions if v["generation info"][0]["is ai generated"]]))     
        print(f"get_models_used called: {models}")
        return models

    def get_new_version(self, new_version_name, old_version_name, generation_info_dict, new_content_dict, new_costs_dict, new_editing_dict, new_notes_dict):
        new_and_old_data_dict = self.combine_new_and_old(generation_info_dict, new_costs_dict, new_editing_dict, new_notes_dict)
        comparisons_dicts = self.get_comparisons_dicts(old_version_name)
        new_version = {"version name": new_version_name, "content": new_content_dict, **new_and_old_data_dict, "comparisons": comparisons_dicts} 
        return new_version  

    def get_prompt_name_from_base(self):
        return self.versions[-1]["generation info"][0]["prompt name"]

    def get_timestamp(self):
        return time.strftime("%Y-%m-%d-%H%M-%S")

    def get_version_name(self, created_by):
        return f"{created_by}-{self.time_started}"                 

    def initialize_versions(self, new_version_name):
        d = {
            "costs":  [{"version name": new_version_name} | {cost: 0 for cost in self.get_costs_list()}],
            "notes":  [{"version name": new_version_name} | {fieldname: [] for fieldname in self.content_fieldnames}],
            "editing": [{}],
            "generation info": [{}]
            }
        self.versions.append(d)  

    def is_same_user(self, created_by):
        return self.versions[0]["generation info"][0]["created by"] == created_by

    def load_versions(self):
        filename = self.get_legal_json_filename()
        print(f"Loading {filename}")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERROR!!! No filename: {filename}")
            return [] 

    def save_to_json(self, content):
        filename = self.get_legal_json_filename()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)           

    def update_content(self, content, new_version_name, is_ai_generated):
        new_content = {}
        new_notes = {}
        for fieldname, fieldvalue in content.items():
            new_content[fieldname] = {}
            if is_ai_generated:
                new_content[fieldname]["value"] = fieldvalue 
                new_content[fieldname]["notes"] = ""
            else:
                new_content[fieldname]["value"] = fieldvalue["value"]
                if "new notes" in fieldvalue and fieldvalue["new notes"]:
                    new_content[fieldname]["notes"] = f"{new_version_name}: {fieldvalue['new notes']}"
                    new_notes[fieldname] = f"{new_version_name}: {fieldvalue['new notes']}"
                else:
                    new_content[fieldname]["notes"] = fieldvalue["notes"] if "notes" in fieldvalue else ""
        return new_content, new_notes

    def update_costs(self, costs, editing, new_version_name):
        time_to_create = editing["time editing"] if editing and "time editing" in editing else (time.time() - time.mktime(time.strptime(self.time_started, "%Y-%m-%d-%H%M-%S"))) / 60
        costs["time to create/edit (mins)"] = time_to_create
        costs_list = ["input tokens", "output tokens", "input cost $", "output cost $", "time to create/edit (mins)"]
        overall_costs_dict = {f"overall {cost}": costs[cost] for cost in costs_list}
        for cost in costs_list:
            for cost_history_dict in self.versions[0]["costs"]:
                overall_costs_dict[f"overall {cost}"] += cost_history_dict[cost]
        return {"version name": new_version_name} | costs | overall_costs_dict           

    def update_notes(self, new_notes, created_by, new_version_name):
        notes_copy = copy.copy(self.versions[0]["notes"][0])
        notes_copy["version name"] = new_version_name
        for fieldname in self.content_fieldnames:
            if fieldname not in new_notes or not new_notes[fieldname]:
                continue
            notes_copy[fieldname].append(new_notes[fieldname])
        return notes_copy   
            

    


if __name__ == "__main__":
    ref = "https://fm-digital-assets.fieldmuseum.org/2491/485/C0268502F_p.jpg" 
       
                 

