from llm_processing.claude_interface2 import ClaudeImageProcessorThread
from llm_processing.openai_interface2 import GPTImageProcessorThread

class ProcessorManager:
    def __init__(self, api_key_dict, selected_llms, selected_prompt, prompt_text, image_refs, result_queue):
        self.api_key_dict = api_key_dict
        self.selected_llms = selected_llms
        self.selected_prompt = selected_prompt
        self.prompt_text = prompt_text
        self.image_refs = image_refs
        self.result_queue = result_queue
        self.num_in_queue = 0

    def process_images(self):
        processors = []
        for llm in self.selected_llms:
            if "sonnet" in llm:
                processors += [ClaudeImageProcessorThread(self.api_key_dict[f"{llm}_key"], self.selected_prompt, self.prompt_text)]
            if "gpt" in llm:
                processors += [GPTImageProcessorThread(self.api_key_dict[f"{llm}_key"], self.selected_prompt, self.prompt_text)]
        for image_ref_idx, image_ref in enumerate(self.image_refs):
            version_name = "base"
            for proc_idx, processor in enumerate(processors):
                image, transcript_obj, version_name, image_ref = processor.process_image(image_ref, image_ref_idx, version_name)
                if proc_idx==len(processors)-1:
                    self.result_queue.put((image, transcript_obj, version_name, image_ref))
                    self.num_in_queue += 1
                    print(f"llm_manager: {self.num_in_queue = }")
        self.result_queue.put((None, None, None, None))       

