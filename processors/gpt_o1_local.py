
import requests
import base64
from PIL import Image
from io import BytesIO


# Depreciated as o1 is not available for Image + prompt. hopefully it comes later
class GPTo1LocalImageProcessorThread:
    """
    Local-image-based processor for GPT-4o.
    """

    def __init__(self, api_key, prompt_text, local_images, result_queue):
        self.api_key = api_key
        self.prompt_text = prompt_text
        self.local_images = local_images  
        self.result_queue = result_queue
        print("GPT o1 (Local images)")

    def process_images(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        print(f"Starting to process {len(self.local_images)} images")

        for index, (image, filename) in enumerate(self.local_images):
            try:
                print(f"\nProcessing image {index + 1}: {filename}")
                
                print("Converting image to base64...")
                buffered = BytesIO()
                image.save(buffered, format="JPEG")
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
                print("Base64 conversion complete")

                print("Preparing API payload...")
                payload = {
                    "model": "o1-preview",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": self.prompt_text},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 2048,
                    "temperature": 0,
                    "seed": 42
                }

                print("Sending request to OpenAI API...")
                post_resp = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response_data = post_resp.json()
                print("API response received")

                print("Formatting response...")
                output = self.format_response(
                    f"Local Image {index + 1}",
                    response_data,
                    filename
                )
                self.result_queue.put((image, output))
                print(f"Image {index + 1} processing complete")

            except Exception as e:
                error_message = (
                    f"Error processing local image {index+1} ({filename}): {str(e)}"
                )
                print(f"ERROR: {error_message}")
                self.result_queue.put((None, error_message))

        print("\nAll images processed. Sending completion signal.")
        self.result_queue.put((None, None))

    def format_response(self, image_name, response_data, filename):
        print(f"Formatting response for {filename}...")
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0].get("message", {}).get("content", "")
            formatted_result = (
                f"{image_name}\nFilename: {filename}\n\n{content}\n"
            )
            print("Response formatting complete")
        else:
            formatted_result = (
                f"{image_name}\nFilename: {filename}\n\nNo data returned from API.\n"
            )
            print("WARNING: No data returned from API")
        return formatted_result
