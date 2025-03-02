from llm_processing.claude_interface3 import ClaudeImageProcessor
from llm_processing.openai_interface3 import GPTImageProcessor
import llm_processing.utility as utility

class ProcessorManager:
    def __init__(self, api_key_dict, selected_llms, selected_prompt, prompt_text):
        self.api_key_dict = api_key_dict
        self.selected_llms = selected_llms
        self.selected_prompt = selected_prompt
        self.prompt_text = prompt_text
        self.processors = self.set_processors()

    def set_processors(self):
        processors = []
        for llm in self.selected_llms:
            if "sonnet" in llm:
                processors += [ClaudeImageProcessor(self.api_key_dict[f"{llm}_key"], self.selected_prompt, self.prompt_text)]
            if "gpt" in llm:
                processors += [GPTImageProcessor(self.api_key_dict[f"{llm}_key"], self.selected_prompt, self.prompt_text)]
        return processors

    def get_base64_image_and_ref(self, image_info):
        if type(image_info)==str:
            image_ref = image_info
            image = utility.get_image_from_url(image_info)
        else:
            image, image_ref = image_info
            image = image_info
        return utility.get_base64_image(image), image, image_ref
        
    def process_one_image(self, image_ref_idx, image_info):
        base64_image, image, image_ref = self.get_base64_image_and_ref(image_info)     
        version_name = "base"
        for proc_idx, processor in enumerate(self.processors):
            transcript_obj, version_name = processor.process_image(base64_image, image_ref, image_ref_idx, version_name)
        return image, transcript_obj, version_name, image_ref
    

