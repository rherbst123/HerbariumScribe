import requests
import base64
from PIL import Image
from io import BytesIO

class GPTo1mageProcessorThread:
    """
    URL-based processor for GPT-o1.
    """

    def __init__(self, api_key, prompt_text, urls, result_queue):
        self.api_key = api_key
        self.prompt_text = prompt_text
        self.urls = urls
        self.result_queue = result_queue
        print("GPT o1 (URL-based)")
        def process_images(self):
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            print("Starting to process images...")

            for index, url in enumerate(self.urls):
                url = url.strip()
                print(f"\nProcessing Image {index + 1} from URL: {url}")
                try:
                    print("  Downloading image...")
                    response = requests.get(url)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
                    print("  Image downloaded successfully")

                    print("  Converting image to base64...")
                    buffered = BytesIO()
                    image.save(buffered, format="JPEG")
                    base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    print("  Base64 conversion complete")

                    print("  Preparing API request payload...")
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

                    print("  Sending request to OpenAI API...")
                    post_resp = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    response_data = post_resp.json()
                    print("  Received response from API")

                    output = self.format_response(f"Image {index + 1}", response_data, url)
                    self.result_queue.put((image, output))
                    print(f"  Image {index + 1} processing complete")

                except requests.exceptions.RequestException as e:
                    error_message = (
                        f"Error processing image {index + 1} from URL '{url}': {str(e)}"
                    )
                    print(f"  ERROR: {error_message}")
                    self.result_queue.put((None, error_message))

            print("\nAll images processed. Sending completion signal.")
            self.result_queue.put((None, None))

    def format_response(self, image_name, response_data, url):
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0].get("message", {}).get("content", "")
            formatted_result = f"{image_name}\nURL: {url}\n\n{content}\n"
        else:
            formatted_result = (
                f"{image_name}\nURL: {url}\n\nNo data returned from API.\n"
            )
        return formatted_result
