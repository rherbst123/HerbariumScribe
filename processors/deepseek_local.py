import requests
import base64
from PIL import Image
from io import BytesIO
import logging
from queue import Queue
from typing import List, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekLocalImageProcessorThread:
    """
    Local-image-based processor for DeepSeek-Vision.
    """

    def __init__(self, api_key: str, prompt_text: str, local_images: List[Tuple[Image.Image, str]], result_queue: Queue):
        self.api_key = api_key
        self.prompt_text = prompt_text
        self.local_images = local_images  # List of (PIL Image, filename)
        self.result_queue = result_queue
        logger.info("Initializing DeepSeekImageProcessor (Local images)")

    def process_images(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        logger.info(f"Starting to process {len(self.local_images)} images")

        for index, (image, filename) in enumerate(self.local_images):
            try:
                logger.info(f"\nProcessing image {index + 1}: {filename}")
                
                # Convert image to base64
                logger.info("Converting image to base64...")
                buffered = BytesIO()
                image.save(buffered, format="JPEG")  # Ensure the API supports JPEG
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
                logger.info("Base64 conversion complete")

                # Prepare API payload
                logger.info("Preparing API payload...")
                payload = {
                    "model": "deepseek-reasoner",
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
                    "temperature": 0
                }

                # Send request to DeepSeek API
                logger.info("Sending request to DeepSeek API...")
                post_resp = requests.post(
                    "https://api.deepseek.com/v1/vision/analyze",  # Verify endpoint
                    headers=headers,
                    json=payload
                )
                post_resp.raise_for_status()  # Raise an exception for HTTP errors
                response_data = post_resp.json()
                logger.info("API response received")

                # Format response
                logger.info("Formatting response...")
                output = self.format_response(
                    f"Local Image {index + 1}",
                    response_data,
                    filename
                )
                self.result_queue.put((image, output))
                logger.info(f"Image {index + 1} processing complete")

            except requests.exceptions.RequestException as e:
                error_message = f"API error processing local image {index+1} ({filename}): {str(e)}"
                logger.error(error_message)
                self.result_queue.put((None, error_message))
            except Exception as e:
                error_message = f"Unexpected error processing local image {index+1} ({filename}): {str(e)}"
                logger.error(error_message, exc_info=True)
                self.result_queue.put((None, error_message))

        logger.info("\nAll images processed. Sending completion signal.")
        self.result_queue.put((None, None))

    def format_response(self, image_name: str, response_data: dict, filename: str) -> str:
        logger.info(f"Formatting response for {filename}...")
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0].get("message", {}).get("content", "")
            formatted_result = (
                f"{image_name}\nFilename: {filename}\n\n{content}\n"
            )
            logger.info("Response formatting complete")
        else:
            formatted_result = (
                f"{image_name}\nFilename: {filename}\n\nNo data returned from API.\n"
            )
            logger.warning("No data returned from API")
        return formatted_result