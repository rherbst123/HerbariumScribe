#from llm_processing.llm_manager_testing import ProcessorManager
from llm_processing.llm_manager4 import ProcessorManager
from llm_processing.transcript6 import Transcript

class JobsRunner:
    def __init__(self, msg, user_name):
        self.msg = msg 
        self.user_name = user_name 
        self.jobs_dict = self.get_blank_jobs_dict()

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

    def get_transcript_objs(self):
        return self.jobs_dict["transcript_objs"]

    def get_transcript_pages(self):
        return self.jobs_dict["pages"]                 

    def load_jobs(self, jobs_dict):
        for job_name, job in jobs_dict.items():
            self.jobs_dict[job_name] = job
    
    def process_jobs(self):
        self.msg["status"] = []
        jobs = self.jobs_dict
        processor_manager = ProcessorManager(self.msg, jobs["api_key_dict"], jobs["selected_llms"], jobs["selected_prompt_name"], jobs["prompt_text"])
        copy_images_to_process = jobs["to_process"].copy()
        for idx, image_to_process in enumerate(copy_images_to_process):
            jobs["to_process"].remove(image_to_process)
            jobs["in_process"].append(image_to_process)
            image, transcript_obj, version_name, image_ref = processor_manager.process_one_image(idx, image_to_process)
            if type(transcript_obj) != Transcript:
                print(f"Error processing {image_ref}")
                print(f"Error: {transcript_obj}")
                self.msg["pause_button_enabled"] = True
                self.msg["status"].append(transcript_obj)
                jobs["failed"].append(image_to_process)
            else:
                version_name = transcript_obj.create_new_version_for_user(self.user_name)
                d = {"image": image, "transcript_obj": transcript_obj, "version_name": version_name, "image_ref": image_ref}
                print(f"Successfully processed {image_ref}")
                self.msg["status"].append(f"Successfully processed {image_ref}\n")
                jobs["processed"].append([image_to_process, image_ref])
                jobs["transcript_objs"].append(transcript_obj)
                jobs["pages"].append(d)
        if self.jobs_dict["transcript_objs"]:
            self.msg["pause_button_enabled"] = False
            self.msg["success"] = "Images processed successfully!"
        else:
            print("Error!!!!")
            self.msg["warning"] = "No images or errors occurred. Check logs or outputs."
            self.msg["pause_button_enabled"] = False

    def resume_jobs(self, try_failed_jobs):
        if try_failed_jobs:
            failed_jobs = []
            for job in self.jobs_dict["failed"]:
                if job not in failed_jobs:
                    failed_jobs.append(job)
            self.jobs_dict["to_process"] = failed_jobs + self.jobs_dict["to_process"]
        self.process_jobs()                