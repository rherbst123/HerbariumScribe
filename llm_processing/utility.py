import re
import requests
from PIL import Image
from io import BytesIO
import base64
import base64

def extract_info_from_text(formatted_transcription):
        regex_patterns = {
        'verbatimCollectors': r"verbatimCollectors: (.+?)\n",
        'collectedBy': r"collectedBy: (.+?)\n",
        'secondaryCollectors': r"secondaryCollectors: (.+?)\n",
        'recordNumber': r"recordNumber: (.+?)\n",
        'verbatimEventDate': r"verbatimEventDate: (.+?)\n",
        'minimumEventDate': r"minimumEventDate: (.+?)\n",
        'maximumEventDate': r"maximumEventDate: (.+?)\n",
        'verbatimIdentification': r"verbatimIdentification: (.+?)\n",
        'latestScientificName': r"latestScientificName: (.+?)\n",
        'identifiedBy': r"identifiedBy: (.+?)\n",
        'verbatimDateIdentified': r"verbatimDateIdentified: (.+?)\n",
        'associatedTaxa': r"associatedTaxa: (.+?)\n",
        'country': r"country: (.+?)\n",
        'firstPoliticalUnit': r"firstPoliticalUnit: (.+?)\n",
        'secondPoliticalUnit': r"secondPoliticalUnit: (.+?)\n",
        'municipality': r"municipality: (.+?)\n",
        'verbatimLocality': r"verbatimLocality: (.+?)\n",
        'locality': r"locality: (.+?)\n",
        'habitat': r"habitat: (.+?)\n",
        'verbatimElevation': r"verbatimElevation: (.+?)\n",
        'verbatimCoordinates': r"verbatimCoordinates: (.+?)\n",
        'otherCatalogNumbers': r"otherCatalogNumbers: (.+?)\n",
        'originalMethod': r"originalMethod: (.+?)\n",
        'typeStatus': r"typeStatus: (.+?)\n",
        }
        result = {}
        for key, pattern in regex_patterns.items():
            match = re.search(pattern, formatted_transcription)
            result[key] = match.group(1).strip() if match else f""
        return result if any(result.values()) else formatted_transcription

def convert_from_camelcase(s):
    words = re.findall(r'[A-Z]?[a-z]+', s)
    return ' '.join(words).lower()

def dict_to_string(dictionary):
    result = ""
    for key, value in dictionary.items():
        result += f"{key}: {value}\n"
    return result.strip()

def get_image_from_url(url):
    try:
        response = requests.get(url.strip())
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        return image
    except requests.exceptions.RequestException as e:
        error_message = f"Error processing image: '{url}': {str(e)}"
        print(f"ERROR: {error_message}")
        return error_message

def get_base64_image(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str
                

if __name__ == "__main__":
    formatted_transcription = """
    verbatimCollectors: 
    collectedBy: 
    secondaryCollectors: 
    recordNumber: 
    verbatimEventDate: 
    minimumEventDate: 
    maximumEventDate: 
    verbatimIdentification: 
    latestScientificName: 
    identifiedBy: 
    verbatimDateIdentified:aaaaa 
    associatedTaxa: 
    country: 
    firstPoliticalUnit: 
    secondPoliticalUnit: aa 
    municipality: 
    verbatimLocality: 
    locality: 
    habitat: 
    verbatimElevation: 
    verbatimCoordinates: 
    otherCatalogNumbers: 
    originalMethod: 
    typeStatus: 
    """
    print(type(extract_info_from_text(formatted_transcription)))        