import re
import requests
from PIL import Image
from io import BytesIO
import base64
import csv

def striplines(text):
    text = re.sub("[🥺👍]", "", text)
    return [s.strip() for s in text.splitlines()]
    

def get_fieldnames_from_prompt(prompt_text):
    prompt_text = "\n".join(striplines(prompt_text))
    fieldnames = re.findall(r"(^\w+):", prompt_text, flags=re.MULTILINE)
    return fieldnames

def get_contents(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def get_contents_from_csv(filename):
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]        

def convert_text_to_dict(text, fieldnames):
    lines = striplines(text)
    result = {fieldname: "" for fieldname in fieldnames}
    for line in lines:
        for fieldname in fieldnames:
            if line.startswith(fieldname):
                result[fieldname] = line.split(":", 1)[1].strip()
    return result if any(result.values()) else {"error": text}        

def extract_info_from_text(text, prompt_name="1.5Stripped.txt"):
    prompt_text = get_contents(f"prompts/{prompt_name}")
    fieldnames = get_fieldnames_from_prompt(prompt_text)
    d = convert_text_to_dict(text, fieldnames)
    return d

def dict_to_string(dictionary):
    result = ""
    for key, value in dictionary.items():
        result += f"{key}: {value}\n"
    return result.strip()

def get_image_name_url(url):
    return url.split("/")[-1]        

def get_image_from_url(url):
    try:
        print(f"Processing image: '{url = }'")
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

def get_image_from_temp_folder(image_name):
    try:
        image = Image.open(f"temp_images/{image_name}")
        base64_image = get_base64_image(image)
        return base64_image
    except Exception as e:
        error_message = f"Error processing image: '{image_name}': {str(e)}"
        print(f"ERROR: {error_message}")
        return error_message    
                

if __name__ == "__main__":
    text = "Here is the transcription and expansion of details from the herbarium label:\n\nverbatimCollectors: leg H Fleischer nr 3-2734\ncollectedBy: Fleischer\nsecondaryCollectors: N/A\nrecordNumber: 3-2734\nverbatimEventDate: 25 9 1903\nminimumEventDate: 1903-09-25\nmaximumEventDate: 1903-09-25\nverbatimIdentification: Macromitrium\nlatestScientificName: Macromitrium austraLieni\nidentifiedBy: N/A\nverbatimDateIdentified: N/A\nassociatedTaxa: N/A\ncountry: Australia\nfirstPoliticalUnit: Queensland\nsecondPoliticalUnit: N/A\nmunicipality: N/A\nverbatimLocality: Eumundi (ca 100 km nordlich Brisbane) Urwald\nlocality: Eumundi, about 100 km north of Brisbane\nhabitat: Urwald (primeval forest)\nsubstrate: N/A\nverbatimElevation: N/A\nverbatimCoordinates: N/A\notherCatalogNumbers: 1076713, 1044984\noriginalMethod: Typed\ntypeStatus: no type status"
    prompt_name = "1.1Stripped.txt" 
    d = extract_info_from_text(text, prompt_name)
    print(d)      