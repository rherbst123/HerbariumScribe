import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import csv
import json
import re
import llm_processing.utility as utility
from llm_processing.transcript6 import Transcript
from llm_processing.volume import Volume

def get_contents_from_csv(csv_file):
    with open(csv_file, "r", encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def get_contents_from_txt(txt_file):
    with open(txt_file, "r", encoding='utf-8') as f:
        return f.read()        

def confirm_volume_name(csv_filename):
    volume_name = input("Enter volume name: ")
    modelname = input("Enter model name: ") 
    return volume_name, modelname

def get_transcript_content(image_data, fieldnames):
    return {fieldname: image_data[fieldname]  if fieldname in image_data else "" for fieldname in fieldnames}   

def process_dicts(unprocessed_dicts, fieldnames, prompt_filename, modelname, image_ref_name, is_ai_generated, all_costs=None):
    pages = []
    print(f"{unprocessed_dicts = }")
    for image_data in unprocessed_dicts:
        print(f"{image_data = }")
        image_ref = image_data[image_ref_name]
        image = utility.get_image_from_temp_folder(image_ref)
        transcript_obj = Transcript(image_ref, prompt_filename)
        transcript_obj.initialize_versions()
        content = get_transcript_content(image_data, fieldnames)
        costs = transcript_obj.get_blank_costs_dict() if not all_costs else all_costs[image_ref]
        version_name = transcript_obj.create_transcription_from_ai(content, modelname, costs, old_version_name="base", is_ai_generated=is_ai_generated)
        page = {"image": image, "transcript_obj": transcript_obj, "version_name": version_name, "image_ref": image_ref}
        pages.append(page)
    return pages

def convert(data, prompt_folder, prompt_filename, image_ref_name, volume_name, modelname, is_ai_generated=True, all_costs=None):
    msg = {}
    volume = Volume(msg, volume_name)
    prompt_text = get_contents_from_txt(prompt_folder+prompt_filename)
    fieldnames = utility.get_fieldnames_from_prompt(prompt_text)
    pages = process_dicts(data, fieldnames, prompt_filename, modelname, image_ref_name, is_ai_generated, all_costs)
    for page in pages:
        volume.add_page(page)
    volume.commit_volume()  # committing volume saves the volume and all its pages
    print("Volume committed")   

def main(csv_filename, prompt_folder, prompt_filename, image_ref_name):
    volume_name, modelname = confirm_volume_name(csv_filename)
    unprocessed_dicts = get_contents_from_csv(csv_filename)
    convert(unprocessed_dicts, prompt_folder, prompt_filename, image_ref_name, volume_name, modelname)

if __name__ == "__main__":
    csv_filename = "C:/Users/dancs/OneDrive/Documents/GitHub/FieldMuseumTranscription/DataAnalysis/Trillo/Transcriptions/12-trillo-flowering-transcriptions.csv"
    prompt_folder = "prompts/"
    prompt_filename = "Prompt 1.5.4.txt"
    image_ref_name = "docName"
    main(csv_filename, prompt_folder, prompt_filename, image_ref_name)