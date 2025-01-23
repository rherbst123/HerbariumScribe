# claude_local.py
import anthropic
import base64
from PIL import Image
from io import BytesIO

class ClaudeLocalImageProcessorThread:
    """
    Local-image-based processor for Claude.
    """

    def __init__(self, api_key, prompt_text, local_images, result_queue):
        self.api_key = api_key
        self.prompt_text = prompt_text
        self.local_images = local_images
        self.result_queue = result_queue
        self.client = anthropic.Anthropic(api_key=self.api_key)
        print("ClaudeImageProcessor (Local images)")

    def process_images(self):
        for index, (image, filename) in enumerate(self.local_images):
            try:
                buffered = BytesIO()
                image.save(buffered, format="JPEG")
                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

                message = self.client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=2500,
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

                output = self.format_response(
                    f"Local Image {index + 1}",
                    message.content,
                    filename
                )
                self.result_queue.put((image, output))

            except Exception as e:
                error_message = (
                    f"Error processing local image {index+1} ({filename}): {str(e)}"
                )
                self.result_queue.put((None, error_message))

        # Signal complete
        self.result_queue.put((None, None))

    def format_response(self, image_name, response_data, filename):
        text_block = response_data[0].text
        lines = text_block.split("\n")

        formatted_result = f"{image_name}\n"
        formatted_result += f"Filename: {filename}\n\n"
        formatted_result += "\n".join(lines)
        return formatted_result
