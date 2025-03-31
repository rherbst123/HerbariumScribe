from llm_processing.transcript6 import Transcript
import json
import json

class Volume:
    def __init__(self, msg, name):
        self.msg = msg
        self.name = name
        self.volumes_folder = "output/volumes"
        self.pages = []
        self.current_page_idx = 0
        self.current_page = None
        self.field_idx = 0
        self.data = {}

    def add_page(self, d):
        self.pages.append(d)

    def commit_volume(self):
        self.compile_volume_data()
        self.save_volume_to_json()    

    def compile_volume_data(self):
        self.data["costs"] = self.get_volume_costs()
        

    def dict_to_text(self, d):
        return "\n".join([f"{k}: {v['value']}" for k, v in d.items()]) + 8*"\n" 

    def get_blank_overall_costs_dict(self):
            return {
                "overall input tokens": 0,
                "overall output tokens": 0,
                "overall input cost $": 0,
                "overall output cost $": 0,
                "overall time to create/edit (mins)": 0
            }    

    def get_current_fieldname(self):
        return self.current_fieldname

    def get_current_fieldvalue(self):
        return self.current_fieldvalue 

    def get_volume_costs(self):
        costs_list = []
        overall_costs_dict = self.get_blank_overall_costs_dict()
        cost_names = list(overall_costs_dict.keys())
        overall_costs_dict["transcript"] = self.name
        costs_list.append(overall_costs_dict)
        for page in self.pages:
            transcript_obj = page["transcript_obj"]
            transcript_costs_dict = transcript_obj.versions["costs"][-2]
            transcript_name = transcript_obj.image_ref
            d = {"transcript": transcript_name}
            for cost_name in cost_names:
                d[cost_name] = transcript_costs_dict[cost_name] 
                overall_costs_dict[cost_name] += transcript_costs_dict[cost_name] 
            costs_list.append(d)
        return costs_list          

    def save_volume_to_json(self):
        output_dict = {}
        for page in self.pages:
            transcript_obj = page["transcript_obj"]
            image_ref = page["image_ref"]
            output_dict[image_ref] = transcript_obj.versions
        output_dict["volume data"] = self.data    
        with open(f"{self.volumes_folder}/{self.name}-volume.json", "w", encoding="utf-8") as f:
            json.dump(output_dict, f, ensure_ascii=False, indent=4)       

    def set_current_field(self):
        self.current_fieldname = self.fieldnames[self.field_idx]
        self.current_fieldvalue = self.current_output_dict[self.current_fieldname]["value"]        

    def set_current_page(self):  
        self.current_page = self.pages[self.current_page_idx]
        self.current_transcript_obj = self.pages[self.current_page_idx]["transcript_obj"]
        self.current_image = self.pages[self.current_page_idx]["image"]
        self.current_image_ref = self.pages[self.current_page_idx]["image_ref"]
        self.current_version_name = self.pages[self.current_page_idx]["version_name"]
        self.current_output_dict = self.current_transcript_obj.versions["content"][-1]
        self.fieldnames = list(self.current_output_dict.keys())
        self.set_current_field()

    def set_data(self, d):
        self.data = d

    def set_field_idx(self, idx):
        self.field_idx = idx
        self.set_current_field() 

    def set_page_idx(self, idx):
        self.current_page_idx = idx
        self.set_current_page()       

