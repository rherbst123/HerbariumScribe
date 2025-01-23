import anthropic
import base64
import requests
from PIL import Image
from io import BytesIO

class ClaudeImageProcessorThread:
    """
    Claude with URL input 
    """

    def __init__(self, api_key, prompt_text, urls, result_queue):
        self.api_key = api_key
        self.prompt_text = prompt_text
        self.urls = urls
        self.result_queue = result_queue
        self.client = anthropic.Anthropic(api_key=self.api_key)
        print("ClaudeImageProcessor (URL-based)")

    def process_images(self):
        for index, url in enumerate(self.urls):
            url = url.strip()
            print(f"\nProcessing image {index + 1} from URL: {url}")
            
            try:
                print("Downloading image...")
                response = requests.get(url)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                print("Image downloaded and opened successfully")

                print("Converting image to base64...")
                buffered = BytesIO()
                image.save(buffered, format="JPEG")
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
                print("Base64 conversion complete")

                print("Making API call to Claude...")
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4096,
                    temperature=0,
                    system=(
                        "You are an assistant that has a job to extract text from "
                        "an image and parse it out. Only include the text that is "
                        "relevant to the image. Do not Hallucinate"
                    ),
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": self.prompt_text},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": base64_image,
                                    },
                                },
                            ],
                        }
                    ],
                )
                print("API call completed successfully")

                print("Formatting response...")
                output = self.format_response(f"Image {index + 1}", message.content, url)
                self.result_queue.put((image, output))
                print(f"Image {index + 1} processing complete\n")

            except requests.exceptions.RequestException as e:
                error_message = (
                    f"Error processing image {index + 1} from URL '{url}': {str(e)}"
                )
                print(f"ERROR: {error_message}")
                self.result_queue.put((None, error_message))

        print("All images processed")
        self.result_queue.put((None, None))

    def format_response(self, image_name, response_data, url):
        text_block = response_data[0].text
        lines = text_block.split("\n")

        formatted_result = f"{image_name}\n"
        formatted_result += f"URL: {url}\n\n"
        formatted_result += "\n".join(lines)
        return formatted_result
