import re

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
            result[key] = match.group(1).strip() if match else f"no {convert_from_camelcase(key)}"
        return result

def convert_from_camelcase(s):
    words = re.findall(r'[A-Z]?[a-z]+', s)
    return ' '.join(words).lower()

def dict_to_string(dictionary):
    result = ""
    for key, value in dictionary.items():
        result += f"{key}: {value}\n"
    return result.strip()    