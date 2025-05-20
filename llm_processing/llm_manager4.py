import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from llm_processing.claude_interface3 import ClaudeImageProcessor
from llm_processing.openai_interface3 import GPTImageProcessor
from llm_processing.bedrock_interface import create_image_processor
from llm_processing.transcript6 import Transcript
import llm_processing.utility as utility
import json

class LLMManager:
    def __init__(self, msg, api_key_dict, selected_llms, selected_prompt, prompt_text):
        self.msg = msg
        self.api_key_dict = api_key_dict
        self.selected_llms = selected_llms[::-1] # treat the list like a stack: i.e., first selected is run last so that version is returned
        self.selected_prompt = selected_prompt
        self.prompt_text = prompt_text
        self.processors = self.set_processors()
        self.raw_responses_folder = "output/raw_llm_responses"
        self.ensure_directory_exists(self.raw_responses_folder)

    def ensure_directory_exists(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)    

    def save_to_json(self, content, filename):
        with open(filename, 'w') as f:
            json.dump(content, f, indent=4)

    def load_from_json(self, filename):
        with open(filename, 'r') as f:
            return json.load(f)
       
    def set_processors(self):
        processors = []
        for llm in self.selected_llms:
            if "sonnet" in llm and not "bedrock" in llm:
                processors += [ClaudeImageProcessor(self.api_key_dict[f"{llm}_key"], self.selected_prompt, self.prompt_text)]
            elif "gpt" in llm:
                processors += [GPTImageProcessor(self.api_key_dict[f"{llm}_key"], self.selected_prompt, self.prompt_text)]
            elif "bedrock" in llm:
                # Extract the model ID from the llm name (format: "bedrock-modelId")
                model_id = llm.split("-", 1)[1] if "-" in llm else ""
                # Create a shorter model name for display
                model_name = model_id.split(".")[-1] if "." in model_id else model_id
                processors += [create_image_processor("", self.selected_prompt, self.prompt_text, model_id, model_name)]
        return processors

    def fill_out_generation_info_dict(self, transcript_obj, version_name, prior_version_name, modelname):
        generation_info_dict = transcript_obj.get_generation_info_dict(modelname, version_name, prior_version_name, transcript_obj.get_timestamp(), is_ai_generated=True)
        return generation_info_dict

    def fill_out_content_dict(self, content_dict_without_notes):
        return {fieldname: {"value": value, "notes": "", "new notes": ""} for fieldname, value in content_dict_without_notes.items()}     

    def create_version(self, transcript_obj, transcript_text, costs_dict, modelname, prior_version_name):
        version_name = transcript_obj.get_version_name(modelname)
        transcript_obj.intialize_new_version(version_name)
        content_dict_without_notes = utility.convert_text_to_dict(transcript_text, transcript_obj.content_fieldnames)
        filename = f"output/raw_llm_responses/{version_name}-transcript.json"
        self.save_to_json(content_dict_without_notes, filename)
        content_dict = self.fill_out_content_dict(content_dict_without_notes)
        transcript_obj.versions["content"][-1] = content_dict
        generation_info_dict = self.fill_out_generation_info_dict(transcript_obj, version_name, prior_version_name, modelname)
        transcript_obj.versions["generation info"][-1] = generation_info_dict
        transcript_obj.versions["costs"][-1] = costs_dict
        transcript_obj.commit_version()
        return version_name
    
    def process_one_image(self, image_ref_idx, image_info):
        base64_image, image_filename, image = image_info
        transcript_obj = Transcript(image_filename, self.selected_prompt)
        image_ref = transcript_obj.image_ref
        transcript_obj.initialize_versions()
        version_name = "base"
        for proc_idx, processor in enumerate(self.processors):
            transcript_text, costs = processor.process_image(base64_image, image_ref, image_ref_idx)
            version_name = self.create_version(transcript_obj, transcript_text, costs, processor.modelname, version_name)
        return image, transcript_obj, version_name, image_ref