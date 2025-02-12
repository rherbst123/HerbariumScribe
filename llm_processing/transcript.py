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
from llm_processing.compare import TranscriptComparer


class Transcript:
    def __init__(self, image_ref: str, prompt_name: str, time_started=None):
        self.image_ref = image_ref
        self.prompt_name = prompt_name
        self.transcription_folder = "single_transcriptions/"
        self.versions =  self.load_all_versions()
        self.time_started = time_started or self.get_timestamp()

    def download_image(self, url):
        response = requests.get(url)
        image = Image.open(BytesIO(response.content))
        image.save(f"{self.transcription_folder}{self.image_ref}.jpg")    

    def load_all_versions(self):
        filename = self.get_legal_json_filename()
        print(f"Loading {filename}")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {} 

    def get_timestamp(self):
        return time.strftime("%Y-%m-%d-%H%M-%S")  

    def get_version_name(self, created_by):
        return f"{created_by}-{self.time_started}"                 

    def create_version(self, created_by, content, data, is_user=False, old_version_name="base", editing={}):
        self.is_user = is_user
        data = self.update_data(data, created_by, old_version_name)
        new_version_name = self.get_version_name(created_by)
        editing_dict = self.get_editing_dict(created_by, old_version_name) | editing
        self.versions[new_version_name] = {"content": content, "data": data, "editing": editing_dict}
        comparison_dict = self.get_comparsion_dict(old_version_name)
        self.versions[new_version_name] = self.versions[new_version_name] | {f"comparison to old version": comparison_dict}
        self.update_costs(new_version_name)
        self.save_to_json(self.versions)
        return new_version_name

    def get_editing_dict(self, created_by, old_version_name):
        if old_version_name == "base":
            history = [old_version_name]
        else:
            history = self.versions[old_version_name]["editing"]["history"] + [old_version_name]
        return {"time started": 0, "history": history}    

    def get_comparsion_dict(self, old_version_name):
        if old_version_name == "base":
            return {}
        comparer = TranscriptComparer(self)  
        return comparer.compare_last_two_versions()        

    def update_data(self, data, created_by, old_version_name):
        d = {}
        d["prompt name"] = self.prompt_name
        d["created by"] = created_by
        d["is user"] = self.is_user
        d["image ref"] = self.image_ref
        d["old version name"] = old_version_name
        time_to_create = time.time() - time.mktime(time.strptime(self.time_started, "%Y-%m-%d-%H%M-%S"))
        d["time to create/edit"] = time_to_create
        return d | data

    def update_costs(self, current_version_name):
        costs_list = ["input tokens", "output tokens", "input cost $", "output cost $", "time to create/edit"]
        overall_costs_dict = {f"overall {cost}": 0 for cost in costs_list}
        history = self.get_version_history(self.versions, current_version_name)
        for version_name, version in history[::-1]:
            for cost in costs_list:
                overall_costs_dict[f"overall {cost}"] += version["data"][cost]
            self.versions[version_name]["data"] = self.versions[version_name]["data"] | overall_costs_dict

    def update_time_to_edit(self, current_version_name, start=True):
        if start:
            self.versions[current_version_name]["editing"] = {"time started": time.time()}
        else:
            editing_time = time.time() - self.versions[current_version_name]["editing"]["time started"]
            self.versions[current_version_name]["data"]["time to create/edit"] += editing_time
            self.versions[current_version_name]["data"]["overall time to create/edit"] += editing_time
            self.versions[current_version_name]["editing"]["time started"] = 0                   

    def get_version_history(self, versions, current_version_name: str, up_to="base"):
        history = []
        while current_version_name != up_to:
            history.append((current_version_name, versions[current_version_name]))
            current_version_name = versions[current_version_name]["data"]["old version name"]
        return history

    def get_versions_created_by(self, created_by):
        return {version_name: version for version_name, version in self.versions.items() if version["data"]["created by"] == created_by}  

    def get_created_by_history(self, created_by):
        return [self.get_version_history(self.versions, version_name) for version_name in self.get_versions_created_by(created_by).keys()]      

    def sort_version_names_by_date(self, versions):
        timestamp_pattern = r"(\d{4}-\d{2}-\d{2}-\d{4}-\d{2})"
        return sorted(versions.keys(), key=lambda x: re.search(timestamp_pattern, x).group(1), reverse=True)
    
    def sort_versions(self, versions):
        sorted_names = self.sort_version_names_by_date(versions)
        return {name: versions[name] for name in sorted_names}

    def get_latest_version(self, versions):
        latest_version_name = self.sort_version_names_by_date(versions)[0] 
        return latest_version_name, versions[latest_version_name]

    def get_latest_version_name(self):
        return self.sort_version_names_by_date(self.versions)[0]     

    def get_version_by_name(self, version_name):
        return self.versions[version_name]

    def get_field_validation_rating(self, fieldname, version_name):
        if "comparison to old version" not in self.versions[version_name]:
            return 0
        comparison = self.versions[version_name]["comparison to old version"]
        if not comparison or fieldname not in comparison or not math.floor(comparison[fieldname]):
            return 0
        if "created by types" not in comparison:
            return 0    
        created_by_types = comparison["created by types"]
        created_by_types = list(created_by_types)
        return 1 if created_by_types==["model", "model"] else 2 if "model" in created_by_types else 3
  

    
    def get_legal_json_filename(self):
        ref = re.sub(r"[\/]", "#", self.image_ref)
        ref = re.sub(r"[:]", "$", ref)
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
        filename = f"{self.transcription_folder}versions/{ref}-versions.json" 
        return filename   

    def save_to_json(self, versions, sort=True):
        versions = self.sort_versions(versions) if sort else versions
        filename = self.get_legal_json_filename()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(versions, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    ref = "https://fm-digital-assets.fieldmuseum.org/2491/485/C0268502F_p.jpg"
    t = Transcript(ref)
    latest_version = t.get_latest_version()
    print(f"{latest_version = }")             
       
                 

