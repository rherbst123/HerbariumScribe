class ImageProcessor:

    def __init__(self, api_key, prompt_name, prompt_text, model, modelname):
        self.api_key = api_key.strip()
        self.prompt_name = prompt_name
        self.prompt_text = prompt_text
        self.model = model
        self.modelname = modelname
        self.input_tokens = 0
        self.output_tokens = 0
        self.set_token_costs_per_mil()
        self.num_processed = 0
    
    def get_token_costs(self):
        return {
            "input tokens": self.input_tokens,
            "output tokens": self.output_tokens,
            "input cost $": round((self.input_tokens / 1_000_000) * self.input_cost_per_mil, 3),
            "output cost $": round((self.output_tokens / 1_000_000) * self.output_cost_per_mil, 3)
        }         

    def update_usage(self, response_data):
        if "usage" in response_data:
            usage = response_data["usage"]
            self.input_tokens += int(usage.get("prompt_tokens", 0))
            self.output_tokens += int(usage.get("completion_tokens", 0)) 

    def get_transcript_processing_data(self, time_elapsed):
        return {
                "created by": self.modelname,
                "is user": False,
                "time to create/edit": time_elapsed,
                } | self.get_token_costs()               