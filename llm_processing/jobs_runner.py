



#from llm_processing.llm_manager_testing import LLMManager
from llm_processing.llm_manager4 import LLMManager
from llm_processing.transcript6 import Transcript

class JobsRunner:
    def __init__(self, msg, user_name, input_dict, volume):
        self.msg = msg
        self.input_dict = input_dict 
        self.user_name = user_name
        self.volume = volume 
        self.jobs_dict = self.get_blank_jobs_dict()
        self.llm_manager = self.get_llm_manager()
    
    def get_llm_manager(self):
        return LLMManager(self.msg, self.input_dict["api_key_dict"], self.input_dict["selected_llms"], self.input_dict["selected_prompt_filename"], self.input_dict["prompt_text"])        

    def clear_transcript_objs(self):
        self.jobs_dict["transcript_objs"] = [] 

    def clear_transcript_pages(self):
        self.jobs_dict["pages"] = []           

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
            "transcript_objs": [],
            "pages": []
        }

    def get_number_completed_jobs(self):
        return len(self.jobs_dict["processed"])    

    def get_transcript_objs(self):
        return self.jobs_dict["transcript_objs"]

    def get_transcript_pages(self):
        return self.jobs_dict["pages"]                 

    def load_jobs(self, jobs_dict):
        for job_name, job in jobs_dict.items():
            self.jobs_dict[job_name] = job
    
    def process_jobs(self, batch_size=None):
        if not batch_size:
            batch_size = len(self.jobs_dict["to_process"])
        self.msg["status"] = []
        jobs = self.jobs_dict
        copy_images_to_process = jobs["to_process"][:batch_size].copy()
        for idx, image_to_process in enumerate(copy_images_to_process):
            jobs["to_process"].remove(image_to_process)
            jobs["in_process"].append(image_to_process)
            image, transcript_obj, version_name, image_ref = self.llm_manager.process_one_image(idx, image_to_process)
            if type(transcript_obj) != Transcript:
                print(f"Error processing {image_ref}")
                print(f"Error: {transcript_obj}")
                self.msg["pause_button_enabled"] = True
                self.msg["status"].append(transcript_obj)
                jobs["failed"].append(image_to_process)
                return
            else:
                d = {"image": image, "transcript_obj": transcript_obj, "version_name": version_name, "image_ref": image_ref}
                print(f"Successfully processed {image_ref}")
                self.msg["status"].append(f"Successfully processed {image_ref}\n")
                jobs["processed"].append([image_to_process, image_ref])
                jobs["transcript_objs"].append(transcript_obj)
                jobs["pages"].append(d)
                self.volume.add_page(d)
                self.volume.commit_volume()
                version_name = transcript_obj.create_new_version_for_user(self.user_name)
        if self.jobs_dict["transcript_objs"]:
            self.msg["pause_button_enabled"] = False
            self.msg["success"] = "Images processed successfully!"
        else:
            print("Error!!!!")
            self.msg["warning"] = "No images or errors occurred. Check logs or outputs."
            self.msg["pause_button_enabled"] = False

    def resume_jobs(self, try_failed_jobs, batch_size=None):
        if try_failed_jobs:
            failed_jobs = []
            for job in self.jobs_dict["failed"]:
                if job not in failed_jobs:
                    failed_jobs.append(job)
            self.jobs_dict["to_process"] = failed_jobs + self.jobs_dict["to_process"]
            self.jobs_dict["failed"] = []
        self.process_jobs(batch_size)                