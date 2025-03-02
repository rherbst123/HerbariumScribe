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
        self.image_ref = image_ref
        self.prompt_name = prompt_name
        self.transcription_folder = "output/"
        self.versions =  self.load_versions()
        self.time_started = time_started or self.get_timestamp()
        self.prompt_name = prompt_name or self.get_prompt_name_from_base()
        self.models = model or self.get_models_used()

    def download_image(self, url):
        response = requests.get(url)
        image = Image.open(BytesIO(response.content))
        image.save(f"{self.transcription_folder}{self.image_ref}.jpg")    

    def load_versions(self):
        filename = self.get_legal_json_filename()
        print(f"Loading {filename}")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERROR!!! No filename: {filename}")
            return []

    def get_timestamp(self):
        return time.strftime("%Y-%m-%d-%H%M-%S")

    def get_prompt_name_from_base(self):
        return self.versions[-1]["generation info"]["prompt name"]

    def get_models_used(self):
        return list(set([v["generation info"]["created by"] for v in self.versions if v["generation info"]["is ai generated"]]))          

    def get_version_name(self, created_by):
        return f"{created_by}-{self.time_started}"                 

    def create_version(self, created_by, content, costs, is_ai_generated=True, old_version_name="base", editing = {}, new_notes = {}):
        # versions[list[dict]]
        if not self.versions:
            fieldnames = list(content.keys())
            self.initialize_versions(fieldnames)
        new_version_name = self.get_version_name(created_by)    
        generation_info_dict = self.get_generation_info_dict(created_by, old_version_name, self.get_timestamp(), is_ai_generated)
        new_content_dict = self.update_content(content, new_notes, new_version_name, is_ai_generated)
        new_history = self.update_history(new_version_name, created_by)
        new_notes_dict = self.update_notes(new_notes, created_by, new_version_name)    
        new_costs_dict = self.update_costs(costs, editing)
        new_version = {"new version name": new_version_name, "generation info": generation_info_dict, "content": new_content_dict, "costs": new_costs_dict, "editing": editing, "history": new_history, "notes": new_notes_dict}
        comparisons_dict = self.get_comparsions_dict(old_version_name)
        new_version = new_version | {f"comparisons": comparisons_dict}
        if  old_version_name=="base" or self.is_same_user(created_by):
            self.versions[0] = new_version
        else:    
            self.versions.insert(0, new_version)
        self.save_to_json(self.versions)
        return new_version_name

    def initialize_versions(self, fieldnames):
        d = {
            "costs": {cost: 0 for cost in self.get_costs_list()},
            "history": [],
            "notes": {fieldname: [] for fieldname in fieldnames}
            }
        self.versions.append(d)  

    def get_generation_info_dict(self, created_by, old_version_name, time_created, is_ai_generated):
        created_by_type = "model" if is_ai_generated else "user"
        return {"image ref": self.image_ref,"created by": created_by, "time created": time_created, "is ai generated": is_ai_generated, "prompt name": self.prompt_name, "old version name": old_version_name, "created by type": created_by_type}    

    def get_costs_list(self):
        return ["input tokens", "output tokens", "input cost $", "output cost $", "time to create/edit"]
    
    def is_same_user(self, created_by):
        return self.versions[0]["generation info"]["created by"] == created_by

    def update_content(self, content, new_notes, new_version_name, is_ai_generated):
        new_content = {}
        for fieldname, fieldvalue in content.items():
            print(f"{fieldvalue = }")
            new_content[fieldname] = {}
            new_content[fieldname]["value"] = fieldvalue if is_ai_generated else fieldvalue["value"]
            if fieldname in new_notes and new_notes[fieldname]:
                new_content[fieldname]["notes"] = f"{new_version_name}: {new_notes[fieldname]}"
            elif "content" not in self.versions[0]:
                new_content[fieldname]["notes"] = ""
        return new_content

    def update_history(self, new_version_name, created_by):
        history = copy.copy(self.versions[0]["history"])
        print(f"{history = }")
        history.append([new_version_name, created_by])
        return history            

    def update_notes(self, new_notes, created_by, new_version_name):
        notes = copy.copy(self.versions[0]["notes"]) if "notes" in self.versions[0] else {fieldname: "" for fieldname in new_notes.keys()}
        for fieldname, new_note in new_notes.items():
            if not new_note:
                continue
            notes[fieldname].append(f"{new_version_name}: {new_note[fieldname]}")
        return notes   

    def get_comparsions_dict(self, old_version_name):
        if old_version_name == "base":
            return {}
        comparer = TranscriptComparer(self)  
        return comparer.compare_all_versions()        

    def update_costs(self, costs, editing):
        time_to_create = editing["time editing"] if editing and "time editing" in editing else time.time() - time.mktime(time.strptime(self.time_started, "%Y-%m-%d-%H%M-%S"))
        costs["time to create/edit"] = time_to_create
        costs_list = ["input tokens", "output tokens", "input cost $", "output cost $", "time to create/edit"]
        overall_costs_dict = {f"overall {cost}": 0 for cost in costs_list}
        for version in self.versions[::-1]:
            for cost in costs_list:
                overall_costs_dict[f"overall {cost}"] += version["costs"][cost]
        return costs | overall_costs_dict

    def update_time_to_edit(self, start=True):
        if start:
            self.versions[0]["editing"] = {"time started": self.get_timestamp()}
        else:
            time_started = self.versions[0]["editing"]["time started"]
            editing_time = self.get_timestamp() - time.time() - time.mktime(time.strptime(time_started, "%Y-%m-%d-%H%M-%S"))
            self.versions[0]["data"]["time to create/edit"] += editing_time
            self.versions[0]["data"]["overall time to create/edit"] += editing_time
            #self.versions[0]["editing"]["time started"] = 0                   

    def get_field_validation_rating(self, fieldname):
        if "comparisons" not in self.versions[0]:
            return 0
        comparison = self.versions[0]["comparisons"]
        if not comparison or fieldname not in comparison or not math.floor(comparison[fieldname]):
            return 0
        if "created by types" not in comparison:
            return 0    
        created_by_types = comparison["created by types"]
        return 1 if created_by_types==["model", "model"] else 2 if "model" in created_by_types else 3
  
    def get_legal_json_filename(self):
        ref = re.sub(r"[\/]", "#", self.image_ref)
        ref = re.sub(r"[:]", "$", ref)
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
        filename = f"{self.transcription_folder}versions/{ref}-versions.json" 
        return filename   

    def save_to_json(self, content):
        filename = self.get_legal_json_filename()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    ref = "https://fm-digital-assets.fieldmuseum.org/2491/485/C0268502F_p.jpg" 
       
                 

