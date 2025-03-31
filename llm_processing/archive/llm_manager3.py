from llm_processing.claude_interface2 import ClaudeImageProcessorThread
from llm_processing.openai_interface2 import GPTImageProcessorThread

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
                processors += [ClaudeImageProcessorThread(self.api_key_dict[f"{llm}_key"], self.selected_prompt, self.prompt_text)]
            if "gpt" in llm:
                processors += [GPTImageProcessorThread(self.api_key_dict[f"{llm}_key"], self.selected_prompt, self.prompt_text)]
        return processors
    
    def process_one_image(self, image_ref_idx, url=None, local_image=None):
        if url:        
            version_name = "base"
            for proc_idx, processor in enumerate(self.processors):
                image, transcript_obj, version_name, image_ref = processor.process_image_from_url(url, image_ref_idx, version_name)
            return image, transcript_obj, version_name, image_ref
        else:
            version_name = "base"
            for proc_idx, processor in enumerate(self.processors):
                image, transcript_obj, version_name, image_ref = processor.process_local_image(local_image, image_ref_idx, version_name)
            return image, transcript_obj, version_name, image_ref      

