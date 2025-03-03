import streamlit as st
import os
import queue
from datetime import datetime
from PIL import Image
from io import BytesIO
import requests

import time
import json
import re
import pandas as pd


from tkinter import filedialog
import tkinter as tk
from dotenv import load_dotenv
import subprocess
import platform
from streamlit.components.v1 import html

from llm_processing.llm_manager4 import ProcessorManager
from llm_processing.claude_interface3 import ClaudeImageProcessorThread
from llm_processing.transcript5 import Transcript
from llm_processing.utility import extract_info_from_text

# Constants
ENV_FILE = ".env"
REQUIRED_ENV_VARS = {
    "ANTHROPIC_API_KEY": "API key for chat features",
    "LOCAL_IMAGES_FOLDER": "Directory for local images",
    "URL_TXT_FILES_FOLDER": "Directory for URL text files",
    "OPENAI_API_KEY": "Optional OpenAI API key"
}


PROMPT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
TRANCRIPTION_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

def set_up():
    if "session_start_time" not in st.session_state:
        st.session_state.session_start_time = time.time()
    if "overall_session_time" not in st.session_state:
        st.session_state.overall_session_time = 0    
    # inputs
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "session_name" not in st.session_state:
        st.session_state.session_name = ""
    if "urls" not in st.session_state:
        st.session_state.urls = []
    if "prompt_text" not in st.session_state:
        st.session_state.prompt_text = ""
    if "selected_llms" not in st.session_state:
        st.session_state.selected_llms = []
    if "api_key_dict" not in st.session_state:
        st.session_state.api_key_dict = {}
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = f"{st.session_state.user_name}: "
    if "show_chat_area" not in st.session_state:
        st.session_state.show_chat_area = False            
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = ""
    if "selected_prompt" not in st.session_state:
        st.session_state.selected_prompt = ""    
    if "local_images" not in st.session_state:
        st.session_state.local_images = []
    if "job_dict" not in st.session_state:
        st.session_state.job_dict = get_blank_jobs_dict()
    if "files_are_selected_to_process" not in st.session_state:
        st.session_state.files_are_selected_to_process = False     
    # outputs    
    #### elements in st.session_state.processed_outputs elements
    if "status_msg" not in st.session_state:
        st.session_state.status_msg = ""
    if "pause_button_enabled" not in st.session_state:
        st.session_state.pause_button_enabled = False
    if "pause_button_option" not in st.session_state:
        st.session_state.pause_button_option = ""    
    if "processed_images" not in st.session_state:
        st.session_state.processed_images = []
    if "processed_outputs" not in st.session_state:
        st.session_state.processed_outputs = []
    if "processed_version_names" not in st.session_state:
        st.session_state.processed_version_names = []   
    if "processed_image_refs" not in st.session_state:
        st.session_state.processed_image_refs = []
    #### editing output
    if "editor_enabled " not in st.session_state:    
        st.session_state.editor_enabled = False
    if "editing_view_option" not in st.session_state:
        st.session_state.editing_view_option = ""
    
    if "current_full_edits" not in st.session_state:
        st.session_state.current_full_edits = ""
    if "editing_data" not in st.session_state:
        st.session_state.editing_data = []

    if "final_output" not in st.session_state:
        st.session_state.final_output = ""
    if "chat_area" not in st.session_state:
        st.session_state.chat_area = ""
    if "include_image" not in st.session_state:
        st.session_state.include_image = False
    if "show_notes" not in st.session_state:
        st.session_state.show_notes = False
    if "show_notes_msg" not in st.session_state:
        st.session_state.show_notes_msg = "Show Notes"               
    # processing
    if "current_output_dict" not in st.session_state:
        st.session_state.current_output_dict = {}  
    if "filenames_to_edit" not in st.session_state:
        st.session_state.filename_to_edits = []
    if "session_to_edit" not in st.session_state:
        st.session_state.session_to_edit = ""
    if "fieldnames" not in st.session_state:
        st.session_state.fieldnames = []    
    # modes
    if "reedit_mode" not in st.session_state:
        st.session_state.reedit_mode = False
    if "fullscreen" not in st.session_state:
        st.session_state.fullscreen = False
    # current values
    if "current_image_index" not in st.session_state:
        st.session_state.current_image_index = 0        
    if "current_fieldname" not in st.session_state:
        st.session_state.current_fieldname = ""
    if "field_idx" not in st.session_state:
        st.session_state.field_idx = 0    
    if "current_fieldvalue" not in st.session_state:
        st.session_state.current_fieldvalue = ""
    if "content_option" not in st.session_state:
        st.session_state.content_option = "content"
    if "current_transcript_obj" not in st.session_state:
        st.session_state.current_transcript_obj = None 

def reset_states():
    # inputs
    st.session_state.urls.clear()
    st.session_state.local_images.clear()
    # ouputs
    st.session_state.processed_images.clear()
    st.session_state.processed_outputs.clear()
    st.session_state.processed_version_names.clear()
    st.session_state.processed_image_refs.clear()
    st.session_state.final_output = ""
    st.session_state.current_image_index = 0
    st.session_state.editing_data = []
    st.session_state.editor_enabled = False
    st.session_state.show_notes = False
    st.session_state.show_notes_msg = "Show Notes"
    st.session_state.editing_view_option = ""
    # processing
    st.session_state.current_output_dict.clear()
    st.session_state.filename_to_edits.clear()
    st.session_state.session_to_edit = ""
    st.session_state.fieldnames.clear()
    st.session_state.job_dict = get_blank_jobs_dict() 
    st.session_state.files_are_selected_to_process = False  
    # modes
    st.session_state.fullscreen = False
    st.session_state.reedit_mode = False
    # current values
    st.session_state.current_image_index = 0        
    st.session_state.current_fieldname = ""
    st.session_state.field_idx = 0    
    st.session_state.current_fieldvalue = ""
    st.session_state.content_option = "content"
    st.session_state.current_transcript_obj = None 
    st.session_state.chat_history = ""
    st.session_state.show_chat_area = False
    st.session_state.current_chat = ""

def reset_processed_elements():
    st.session_state.processed_images.clear()
    st.session_state.processed_outputs.clear()
    st.session_state.processed_version_names.clear()
    st.session_state.processed_image_refs.clear()
    st.session_state.job_dict = get_blank_jobs_dict() 



# ----------------
# Callback and Support Functions
# ----------------

def append_processed_elements(image, transcript_obj, version_name, image_ref):
    st.session_state.processed_images.append(image)
    st.session_state.processed_outputs.append(transcript_obj)
    st.session_state.processed_version_names.append(version_name)
    st.session_state.processed_image_refs.append(image_ref)
    output_dict = transcript_obj.versions[0]["content"]
    for fieldname in output_dict:
        output_dict[fieldname]["new notes"] = ""
    st.session_state.final_output += image_ref + "\n" + dict_to_text(output_dict) + "\n" + ("=" * 50) + "\n"
    editing_data = {"costs": get_costs_blank_dict(), "editing": get_editing_blank_dict()}
    st.session_state.editing_data.append(editing_data)
    st.session_state.editor_enabled = True

def chat_with_llm():
    if not st.session_state.show_chat_area:
        st.session_state.chat_area = ""
        st.session_state.current_chat = f"claude-3.5-sonnet is available to answer queries. What is your question?\n\n{st.session_state.user_name}: "
        st.session_state.show_chat_area = True
        return
    if not st.session_state.api_key_dict or "claude-3.5-sonnet" not in st.session_state.api_key_dict:
        st.error("Please upload API key file for claude-3.5-sonnet first")
        return
    current_chat = st.session_state.chat_area if st.session_state.chat_area else ""
    if current_chat and current_chat != st.session_state.chat_history:
        # Get the new message (difference between current and history)
        new_message = current_chat[len(st.session_state.chat_history):].strip()
        if new_message:
            try:
                api_key = st.session_state.api_key_dict["claude-3.5-sonnet"].read().decode("utf-8").strip()
                processor = ClaudeImageProcessorThread(api_key, None, None)
                # use a selectbox to ask user if they want to include the url
                if st.session_state.include_image and st.session_state.current_transcript_obj:
                    image = st.session_state.processed_images[st.session_state.current_image_index]
                    response, costs = processor.chat(new_message, image)
                else:
                    response, costs = processor.chat(new_message)
                update_costs(costs)
                st.session_state.chat_history = f"{current_chat}\n\nAssistant: {response}\n\n{st.session_state.user_name}: "
                update_editing({"chats": st.session_state.chat_history})
                st.session_state.current_chat = st.session_state.chat_history
            except Exception as e:
                st.error(f"Error processing chat: {str(e)}")


def color_keys(fieldname):
    if st.session_state.content_option != "content":
        return f":blue[{st.session_state.current_fieldname}]"
    rating = st.session_state.current_transcript_obj.get_field_validation_rating(fieldname)
    return f":red[{st.session_state.current_fieldname}]" if rating==0 else f":orange[{st.session_state.current_fieldname}]" if rating==1 else f":blue[{st.session_state.current_fieldname}]" if rating==2 else f":green[{st.session_state.current_fieldname}]" if rating ==3 else fieldname

def close_chat():
    """Callback to switch 'show_chat_area' off."""
    st.session_state.show_chat_area = False
    new_chat()

def close_fullscreen():
    """Callback to switch 'fullscreen' off."""
    st.session_state.fullscreen = False

def dict_to_text(d):
    return "\n".join([f"🥺 {k}: {v['value']}" for k, v in d.items()]) + 8*"\n"

def enable_notes_display():
    st.session_state.show_notes = not st.session_state.show_notes
    st.session_state.show_notes_msg = "Hide Notes" if st.session_state.show_notes else "Show Notes"    

def get_content_options():
    if st.session_state.current_transcript_obj:
        options = list(st.session_state.current_transcript_obj.versions[0].keys())
        #return [o if o != "content" else "transcript" for o in options ]
        return ["transcript", "comparisons", "costs"]
    else:
        return ["transcript"]
        
def get_costs_blank_dict():
        return {
            "input tokens": 0,
            "output tokens": 0,
            "input cost $": 0,
            "output cost $": 0
        }


def get_editing_blank_dict():
    return {"time started": 0, "time editing": 0, "chats": ""}    

def get_legal_json_filename(image_ref):
        ref = re.sub(r"[\/]", "#", image_ref)
        ref = re.sub(r"[:]", "$", ref)
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
        filename = f"{TRANCRIPTION_FOLDER}/transcripts/{ref}-transcript.json" 
        return filename

def get_blank_jobs_dict():
    return {
        "api_key_dict": {},
        "selected_llms": [],
        "selected_prompt_file": "",
        "prompt_text": "",
        "urls": [],
        "local_images_list": [],
        "to_process": [],
        "in_process": [],
        "processed": [],
        "failed": [],
    }         



def get_combined_output_as_text():
    if not st.session_state.processed_images:
        return "No output to display"
    output = ""
    header = f"Transcription: {len(st.session_state.processed_images)} images\n\n"
    for image, transcript_obj, version_name, image_ref in zip(st.session_state.processed_images, st.session_state.processed_outputs, st.session_state.processed_version_names, st.session_state.processed_image_refs):
        prompt_used = transcript_obj.prompt_name
        models_used = ", ".join(transcript_obj.models)
        output_dict = transcript_obj.versions[0]["content"]
        values = "\n".join([f"{fieldname}: {v['value']}" for fieldname, v in output_dict.items()])
        output += f'{image_ref}\nprompt used: {prompt_used}\nmodel(s) used: {models_used}\n\n{values}\n\n{"=" * 50}\n\n'
    return header + "\n" + output 

def get_option_dict_from_version_in_processed_outputs():
    return st.session_state.processed_outputs[st.session_state.current_image_index].versions[0][st.session_state.content_option]       

def get_timestamp():
    return  time.strftime("%Y-%m-%d-%H%M-%S")

def get_val_from_version_in_processed_outputs():
    return st.session_state.processed_outputs[st.session_state.current_image_index].versions[0][st.session_state.content_option][st.session_state.current_fieldname]

def get_validation_rating(fieldname):
    if st.session_state.content_option != "content":
        return "?"
    rating = st.session_state.current_transcript_obj.get_field_validation_rating(fieldname)
    return rating if rating is not None else "?"

def get_validation_rating_with_emoji(fieldname):
    if st.session_state.content_option != "content":
        return "🥺"
    rating = st.session_state.current_transcript_obj.get_field_validation_rating(fieldname)
    if rating:
        return rating*"👍"
    return "🥺"    
    #return ":thumbsup:" if rating else ""#":pleading_face:" # "👍"


def go_next_image():
    """
    Moves to the next image, if possible.
    Saves current text from output_text_area into the session.
    """
    if st.session_state.processed_outputs and st.session_state.processed_images:
        update_time_to_edit(start=False)
        if st.session_state.current_image_index < len(st.session_state.processed_images) - 1:
            st.session_state.current_image_index += 1
        else:
            st.session_state.current_image_index = 0
        update_displays()
        update_time_to_edit(start=True)
        
def go_previous_image():
    """
    Moves to the previous image, if possible.
    Saves current text from output_text_area into the session.
    """
    if st.session_state.processed_outputs and st.session_state.processed_images:
        update_time_to_edit(start=False)
        if st.session_state.current_image_index > 0:
            st.session_state.current_image_index -= 1
        else:
            st.session_state.current_image_index = len(st.session_state.processed_images) - 1
        update_displays()
        update_time_to_edit(start=True)

def go_to_next_field():
    if st.session_state.field_idx == len(st.session_state.fieldnames) - 1:
        st.session_state.field_idx = 0
    else:
        st.session_state.field_idx += 1
    update_time_to_edit(start=False)
    

def go_to_previous_field():
    if st.session_state.field_idx == 0:
        st.session_state.field_idx = len(st.session_state.fieldnames) - 1
    else:
        st.session_state.field_idx -= 1
    update_time_to_edit(start=False)

def load_jobs(jobs_dict):
    for job_name, job in jobs_dict.items():
        st.session_state.job_dict[job_name] = job        

def new_chat():
    st.session_state.chat_history = ""
    st.session_state.chat_area = ""
    st.session_state.current_chat = f"{st.session_state.user_name}: "
            

def open_fullscreen():
    """Callback to switch 'fullscreen' on."""
    st.session_state.fullscreen = True

def process_images_callback(
        api_key_dict,
        prompt_text_from_file,
        selected_llms,
        selected_prompt_file,
        input_type,
        url_file,
        local_image_files
        ):
        print(f"process_images_callback: {api_key_dict = }, {url_file = }")
        
        for llm in selected_llms:
            if not api_key_dict.get(f"{llm}_key"):
                st.error(f"Please upload the API key file for {llm}.")
                return
        if not prompt_text_from_file:
            st.error("No prompt text available (folder empty or file missing).")
            return  
        for llm in selected_llms:
            if not api_key_dict.get(f"{llm}_key"):
                try:
                    api_key = api_key_dict[llm].read().decode("utf-8").strip()
                except:
                    st.error(f"Unable to read API key file for {llm}. Check encoding or file format.")
                    return
                api_key_dict[f"{llm}_key"] = api_key
        st.session_state.api_key_dict = api_key_dict
        # Store the chosen model & prompt in session for final output/filename
        st.session_state.selected_llms = selected_llms
        st.session_state.selected_prompt = selected_prompt_file
        # Reset states
        st.session_state.prompt_text = prompt_text_from_file
        st.session_state.processed_images.clear()
        st.session_state.processed_outputs.clear()
        st.session_state.processed_version_names.clear()
        st.session_state.processed_image_refs.clear()
        st.session_state.current_image_index = 0
        st.session_state.final_output = ""
        st.session_state.urls.clear()
        st.session_state.local_images.clear()
        st.session_state.fullscreen = False
        
        if input_type == "URL List":
            if not url_file:
                st.error("Please upload a .txt file containing image URLs.")
                return
            try:
                with open(url_file, "r", encoding="utf-8") as f:
                    urls_content = f.read().strip()
                    urls = urls_content.splitlines()
                #urls_content = url_file.read().decode("utf-8")
                #urls = urls_content.strip().splitlines()
            except:
                st.error("Unable to read URL file. Check encoding or file format.")
                return
            st.session_state.urls = urls
        else:  # Local Images
            if not local_image_files:
                st.error("Please upload at least one image file.")
                return
            local_images_list = []
            for uploaded_file in local_image_files:
                try:
                    image = Image.open(uploaded_file)
                    local_images_list.append((image, uploaded_file))
                except Exception as e:
                    st.warning(f"Could not open {uploaded_file}: {e}")
            st.session_state.local_images = local_images_list
    
        use_url = input_type == "URL List"
        images_to_process = st.session_state.urls if use_url else st.session_state.local_images
        jobs_dict = {
            "api_key_dict": api_key_dict,
            "selected_llms": selected_llms,
            "selected_prompt_file": st.session_state.selected_prompt,
            "prompt_text": st.session_state.prompt_text,
            "urls": st.session_state.urls,
            "local_images_list": st.session_state.local_images,
            "to_process": images_to_process,
            "in_process": [],
            "processed": [],
            "failed": [],
        }
        load_jobs(jobs_dict)
        process_jobs()

def process_jobs():
    jobs = st.session_state.job_dict
    processor_manager = ProcessorManager(jobs["api_key_dict"], jobs["selected_llms"], jobs["selected_prompt_file"], jobs["prompt_text"])
    use_url = jobs["urls"] != []
    copy_images_to_process = jobs["to_process"].copy()
    for idx, image_to_process in enumerate(copy_images_to_process):
        jobs["to_process"].remove(image_to_process)
        jobs["in_process"].append(image_to_process)
        image, transcript_obj, version_name, image_ref = processor_manager.process_one_image(idx, image_to_process) if use_url else processor_manager.process_one_image(idx, image_to_process)
        if type(transcript_obj) != Transcript:
            st.session_state.pause_button_enabled = True
            st.session_state.status_msg = transcript_obj
            jobs["failed"].append(image_to_process)
            update_overall_session_time() 
            return
        else:
            st.session_state.status_msg += f"Successfully processed {image_ref}\n"
            jobs["processed"].append([image_to_process, image_ref])
        append_processed_elements(image, transcript_obj, version_name, image_ref)
        output_dict = transcript_obj.versions[0]["content"]
        st.session_state.final_output = get_combined_output_as_text()
        editing_data = {"costs": get_costs_blank_dict(), "editing": get_editing_blank_dict()}
        st.session_state.editing_data.append(editing_data)
    if st.session_state.processed_images:
        st.session_state.pause_button_enabled = False
        st.success("Images processed successfully!")
    else:
        st.warning("No images or errors occurred. Check logs or outputs.")
    update_overall_session_time()      

def re_edit_saved_versions(selected_reedit_files):
    save_edits_to_json()
    reset_processed_elements()
    reset_states()
    try:
        for selected_file in selected_reedit_files:
            with open(os.path.join(f"{TRANCRIPTION_FOLDER}/versions", selected_file), "r", encoding="utf-8") as rf:
                transcript_dict = json.load(rf)
                latest_version_name = transcript_dict[0]["new version name"]
                latest_version_dict = transcript_dict[0]
                image_ref = latest_version_dict["generation info"]["image ref"]
                transcript_obj = Transcript(image_ref, st.session_state.selected_prompt)
                transcript_obj.versions = transcript_dict
                try:
                    response = requests.get(image_ref)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
                    buffered = BytesIO()
                    image.save(buffered, format="JPEG")
                    append_processed_elements(image, transcript_obj, latest_version_name, image_ref)
                except requests.exceptions.RequestException as e:
                    error_message = f"Error processing image: '{image_ref}': {str(e)}"
                    print(f"ERROR: {error_message}")
                    st.error(error_message)
        st.session_state.final_output = get_combined_output_as_text()            
        st.session_state.current_image_index = 0
        st.session_state.current_transcript_obj = st.session_state.processed_outputs[st.session_state.current_image_index]
        st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()

        #st.session_state.current_transcript_obj = transcript_obj
        st.session_state.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
        st.session_state.field_idx = 0
        st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
        st.session_state.current_fieldvalue = st.session_state.current_output_dict[st.session_state.current_fieldname]["value"]            
    except Exception as e:
            st.error(f"Error loading file: {str(e)}")
    st.session_state.reedit_mode = False
     
def re_edit_session(selected_session_file):
    """Handle loading the selected file"""
    save_edits_to_json()
    reset_processed_elements()
    reset_states()
    try:
        with open(os.path.join(f"{TRANCRIPTION_FOLDER}/sessions", selected_session_file), "r", encoding="utf-8") as rf:
            session_dict = json.load(rf)
            for image_ref, transcript_dict in session_dict.items():
                latest_version_name = transcript_dict[0]["new version name"]
                latest_version_dict = transcript_dict[0]
                image_ref = latest_version_dict["generation info"]["image ref"]
                transcript_obj = Transcript(image_ref, st.session_state.selected_prompt)
                transcript_obj.versions = transcript_dict
                try:
                    response = requests.get(image_ref)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
                    buffered = BytesIO()
                    image.save(buffered, format="JPEG")
                    append_processed_elements(image, transcript_obj, latest_version_name, image_ref)
                except requests.exceptions.RequestException as e:
                    error_message = f"Error processing image: '{image_ref}': {str(e)}"
                    print(f"ERROR: {error_message}")
                    st.error(error_message)
        st.session_state.final_output = get_combined_output_as_text()            
        st.session_state.current_image_index = 0
        st.session_state.current_transcript_obj = st.session_state.processed_outputs[st.session_state.current_image_index]
        st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()

        st.session_state.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
        st.session_state.field_idx = 0
        st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
        st.session_state.current_fieldvalue = st.session_state.current_output_dict[st.session_state.current_fieldname]["value"]            
    except Exception as e:
            st.error(f"Error loading file: {str(e)}")
    st.session_state.reedit_mode = False
    
def resume_jobs(try_failed_jobs=False):
    if try_failed_jobs:
        failed_jobs = []
        for job in st.session_state.job_dict["failed"]:
            if job not in failed_jobs:
                failed_jobs.append(job)
        st.session_state.job_dict["to_process"] = failed_jobs + st.session_state.job_dict["to_process"]
    process_jobs()      

def save_edits_as_text():
    update_overall_session_time()
    st.session_state.final_output = get_combined_output_as_text()
    st.success("Edits + header saved in memory! You can now download below.")
    
def save_edits_to_json():
    update_overall_session_time()
    update_processed_outputs()
    session_output_dict = {}
    for transcript_obj, p_version_name, image_ref, editing_data in zip(st.session_state.processed_outputs, st.session_state.processed_version_names, st.session_state.processed_image_refs, st.session_state.editing_data):
        transcript = Transcript(image_ref, st.session_state.selected_prompt)
        s_version_name = transcript.versions[0]["new version name"]
        print(f"in save_edits_to_json: {s_version_name = }, {p_version_name = }")
        costs = editing_data["costs"]
        print(f"in save_edits_to_json: {costs = }")
        editing = editing_data["editing"]
        print(f"in save_edits_to_json: {editing = }")
        output_dict = transcript_obj.versions[0]["content"]
        save_to_json(output_dict, image_ref)
        transcript.create_version(created_by=st.session_state.user_name, content=output_dict, costs=costs, is_ai_generated=False, old_version_name=s_version_name, editing=editing, new_notes = {})
        session_output_dict[image_ref] = transcript.versions
    session_filename = f"{TRANCRIPTION_FOLDER}/sessions/{st.session_state.user_name}-{get_timestamp()}-session.json"
    if session_output_dict:
        with open(session_filename, 'w', encoding='utf-8') as f:
            json.dump(session_output_dict, f, ensure_ascii=False, indent=4)    

def save_field_text_area():
    if st.session_state.processed_outputs and st.session_state.processed_images and st.session_state.content_option=="content":
        st.session_state.current_output_dict[st.session_state.current_fieldname]["value"] = st.session_state.field_text_area
        update_version_in_processed_outputs(st.session_state.field_text_area)

def save_table_edits(edited_elements, fieldnames, current_output_dict):
    editables = ["value", "new notes"]
    for row_number, columns in edited_elements.items():
        for header, val in columns.items():
            if header in editables:
                st.session_state.current_output_dict[fieldnames[row_number]][header] = val
        st.session_state.current_output_dict = current_output_dict        

def save_to_json(content, image_ref):
    update_overall_session_time()
    filename = get_legal_json_filename(image_ref)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

def save_transcription_val():    
    """
    Helper: saves text area changes to st.session_state.processed_outputs.
    """
    if "processed_outputs" in st.session_state and "output_text_area" in st.session_state and st.session_state.content_option=="content":
        idx = st.session_state.current_image_index -1
        if idx < len(st.session_state.processed_outputs):
            st.session_state.processed_outputs[idx][st.session_state.content_option][st.session_state.current_fieldname] = st.session_state.output_text_area

def set_session_name():
    timestamp = get_timestamp() 
    st.session_state.session_name = f"{st.session_state.user_name}-{timestamp}" 

def show_fullscreen_image():
    """
    Displays the current image in a 'full screen' style section,
    plus a button to close it.
    """
    st.write("## Full-Screen Image Viewer")
    idx = st.session_state.current_image_index
    image = st.session_state.processed_images[idx]
    st.image(image, caption=f"Full Screen of Image {idx + 1}", use_container_width=True)
    st.button("Close Full Screen", on_click=close_fullscreen)

def sort_filenames_by_timestamp(filenames):
        timestamp_pattern = r"(\d{4}-\d{2}-\d{2}-\d{4}-\d{2})"
        return sorted(filenames, key=lambda x: re.search(timestamp_pattern, x).group(1), reverse=True)    

def update_costs(new_costs: dict):
    if st.session_state.processed_outputs:
        old_costs = st.session_state.editing_data[st.session_state.current_image_index]["costs"]
        for cost_name, val in new_costs.items():
            old_costs[cost_name] += val

def update_displays():
    st.session_state.current_transcript_obj = st.session_state.processed_outputs[st.session_state.current_image_index]
    st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()
    st.session_state.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
    st.session_state.field_idx = 0
    if st.session_state.content_option=="content":
        st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
        st.session_state.current_fieldvalue = st.session_state.current_output_dict[st.session_state.current_fieldname]["value"]
                   
def update_editing(new_notes: dict):
    if st.session_state.processed_outputs:
        old_notes = st.session_state.editing_data[st.session_state.current_image_index]["editing"]
        for note_name, val in new_notes.items():
            old_notes[note_name] += val  

def update_fieldvalue():
    fieldvalue = st.session_state.fieldvalue_key
    st.session_state.current_output_dict[st.session_state.current_fieldname]["value"] = fieldvalue

def update_text_output():
    current_output_as_text = st.session_state.text_output_key
    output_dict = extract_info_from_text(current_output_as_text)
    for fieldname, fieldvalue in output_dict.items():
        st.session_state.current_output_dict[fieldname]["value"] = fieldvalue   

def update_overall_session_time():
    st.session_state.overall_session_time = time.time() - st.session_state.session_start_time

def update_time_to_edit(start=True):
    update_overall_session_time()
    if st.session_state.processed_outputs:
        old_notes = st.session_state.editing_data[st.session_state.current_image_index]["editing"]
        start_time = get_timestamp() if start else old_notes["time started"]
        if type(start_time)==str: 
            new_editing_time = time.time() - time.mktime(time.strptime(start_time, "%Y-%m-%d-%H%M-%S"))
        else:
            new_editing_time = time.time() - start_time    
        old_notes["time started"] = start_time
        old_notes["time editing"] += new_editing_time

def update_version_in_processed_outputs(val):
    if st.session_state.content_option=="content":
        st.session_state.processed_outputs[st.session_state.current_image_index].versions[0][st.session_state.content_option][st.session_state.current_fieldname]["value"] = val

def update_processed_outputs():
    if st.session_state.content_option=="content" and st.session_state.processed_outputs:
        output_dict = st.session_state.current_output_dict
        st.session_state.processed_outputs[st.session_state.current_image_index].versions[0][st.session_state.content_option] = output_dict    

# State Management
def init_session_state():
    """Initialize session state variables"""
    if 'config' not in st.session_state:
        st.session_state.config = {}
    if 'images_dir' not in st.session_state:
        st.session_state.images_dir = ""
    if 'url_dir' not in st.session_state:
        st.session_state.url_dir = ""
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'env_loaded' not in st.session_state:
        st.session_state.env_loaded = False

# Environment File Handling
def check_env_file():
    """Check if .env file exists and load it"""
    if os.path.exists(ENV_FILE):
        load_dotenv()
        env_vars = {key: os.getenv(key) for key in REQUIRED_ENV_VARS.keys()}
        return env_vars
    return None

def load_env_to_session():
    """Load environment variables into session state"""
    env_vars = check_env_file()
    if env_vars:
        st.session_state.config = env_vars
        st.session_state.images_dir = env_vars.get('LOCAL_IMAGES_FOLDER', '')
        st.session_state.url_dir = env_vars.get('URL_TXT_FILES_FOLDER', '')
        st.session_state.env_loaded = True
        return True
    return False

def select_files(file_types=None, initial_dir=None):
    """Open native file selection dialog that allows multiple file selection"""
    try:
        # Create and hide the tkinter root window
        root = tk.Tk()
        root.attributes('-topmost', True)  # Make sure it appears on top
        root.withdraw()  # Hide the main window
        
        # Default file types if none specified
        if file_types is None:
            file_types = [
                ('Image files', '*.png *.jpg *.jpeg'),
                ('All files', '*.*')
            ]
            
        # Use provided initial directory or expand user's home directory
        dir_value = initial_dir or "~"
        default_dir = os.path.expanduser(dir_value)
        
        # Open the file selection dialog
        file_paths = filedialog.askopenfilenames(
            parent=root,
            initialdir=default_dir,
            title="Select files",
            filetypes=file_types
        )
        
        # Clean up the tkinter instance
        root.destroy()
        
        return file_paths if file_paths else None
        
    except Exception as e:
        st.error(f"Error selecting files: {str(e)}")
        return None

def main():
    st.title("HerbariumScribe")
    
    # Initialize session state
    init_session_state()
    
    
    # Check for existing configuration
    if not st.session_state.env_loaded:
        if load_env_to_session():
            st.success("Existing configuration loaded from .env file")

    # Rest of your main function...


def main():
    st.set_page_config(page_title="Herbarium Parser (Callbacks, with Model & Prompt in Output)", layout="wide")
    init_session_state()
    
    # Initialize file selection states if not present
    if 'select_images_clicked' not in st.session_state:
        st.session_state.select_images_clicked = False
    if 'select_url_clicked' not in st.session_state:
        st.session_state.select_url_clicked = False
    if 'selected_files' not in st.session_state:
        st.session_state.selected_files = None
    if 'selected_url_file' not in st.session_state:
        st.session_state.selected_url_file = None
    
    # Check for existing configuration
    if not st.session_state.env_loaded:
        if load_env_to_session():
            st.success("Existing configuration loaded from .env file")

    st.markdown("""
        <style>
        div.stButton > button {
            background-color: #E0E0E0 ;
        }
        [data-testid="stHorizontalBlock"] {
            background-color: #FFFDD0 !important;  /* Added !important */
            /*padding: .5rem !important;*/
            border-radius: 5px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    set_up()
    st.session_state.user_name = st.text_input("username:", value=st.session_state.user_name)
    if st.session_state.user_name == "":
        st.warning("Please enter your name.")
        st.stop()
    set_session_name()
    update_overall_session_time()
    processing_type = st.radio("Select Processing Operation:", ["Process New Images", "Edit Saved Processed Images"])
    if processing_type == "Process New Images":
        #reset_processed_elements()
        # ---------------
        # Input Settings
        # ---------------
        input_settings_container = st.container(border=True)
        with input_settings_container:
                
            st.write("## Input Settings")
            # ---------------
            # Prompt Selection
            # ---------------
            if not os.path.isdir(PROMPT_FOLDER):
                st.warning(f"Prompt folder '{PROMPT_FOLDER}' does not exist.")
                prompt_files = []
            else:
                prompt_files = [f for f in os.listdir(PROMPT_FOLDER) if f.endswith(".txt")]
                prompt_files.sort()

            if prompt_files:
                selected_prompt_file = st.selectbox("Select a Prompt:", prompt_files)
                with open(os.path.join(PROMPT_FOLDER, selected_prompt_file), "r", encoding="utf-8") as pf:
                    prompt_text_from_file = pf.read().strip()
            else:
                st.warning("No .txt prompt files found in the prompt folder.")
                selected_prompt_file = ""
                prompt_text_from_file = ""


            # LLM Choice
            llm_options = ["claude-3.5-sonnet", "gpt-4o"]
            selected_llms = st.multiselect("Select LLM(s):", llm_options, default=[llm_options[0]])
            api_key_dict = {}
            if "OPENAI_API_KEY" in os.environ:
                api_key_dict["gpt-4o_key"] = os.getenv("OPENAI_API_KEY")
                api_key_dict["gpt-4o_key"] = os.getenv("OPENAI_API_KEY")
            if "ANTHROPIC_API_KEY" in os.environ:
                api_key_dict["claude-3.5-sonnet_key"] = os.getenv("ANTHROPIC_API_KEY")
                api_key_dict["claude-3.5-sonnet_key"] = os.getenv("ANTHROPIC_API_KEY")
            for llm in selected_llms:
                if f"{llm}_key" in api_key_dict:
                    continue
                api_key_dict[llm] = st.file_uploader(f"Upload API Key File For {llm} (TXT)", type=["txt"])
            st.session_state.api_key_dict = api_key_dict
            # Radio for "Local Images" vs. "URL List"
                    
            # Input type selection without default
            input_type = st.radio(
                "Select Image Input Type:",
                ["", "URL List", "Local Images"],
                index=0,
                label_visibility="visible"
            )

            if input_type == "URL List":
                # Button for URL file selection
                if st.button("Select URL File", key='select_url_button'):
                    st.session_state.select_url_clicked = True
                    st.session_state.select_images_clicked = False  # Reset other button

                # Handle URL file selection
                if st.session_state.select_url_clicked:
                    file_paths = select_files(
                        file_types=[('Text files', '*.txt')],
                        initial_dir=st.session_state.url_dir
                    )
                    if file_paths:
                        # Since we only want one URL file, take the first selected file
                        st.session_state.selected_url_file = file_paths[0]
                    st.session_state.select_url_clicked = False
                    st.rerun()

                # Display selected URL file
                if st.session_state.selected_url_file:
                    st.write(f"Selected URL file: {os.path.basename(st.session_state.selected_url_file)}")
                    # Read the URL file
                    try:
                        with open(st.session_state.selected_url_file, 'r') as f:
                            urls_content = f.read()
                            urls = urls_content.strip().splitlines()
                            st.write(f"Found {len(urls)} URLs in file")
                        url_file = st.session_state.selected_url_file
                    except Exception as e:
                        st.error(f"Error reading URL file: {str(e)}")
                        url_file = None
                else:
                    url_file = None
                local_image_files = None

            elif input_type == "Local Images":
                # Button for image selection
                if st.button("Select Image Files", key='select_images_button'):
                    st.session_state.select_images_clicked = True
                    st.session_state.select_url_clicked = False  # Reset other button

                # Handle image file selection
                if st.session_state.select_images_clicked:
                    file_paths = select_files(
                        file_types=[
                            ('Image files', '*.png *.jpg *.jpeg'),
                            ('All files', '*.*')
                        ],
                        initial_dir=st.session_state.images_dir
                    )
                    if file_paths:
                        st.session_state.selected_files = file_paths
                    st.session_state.select_images_clicked = False
                    st.rerun()
                
                # Display selected image files
                if st.session_state.selected_files:
                    st.write("Selected files:")
                    for file in st.session_state.selected_files:
                        st.write(f"- {os.path.basename(file)}")
                    local_image_files = st.session_state.selected_files
                else:
                    local_image_files = None
                url_file = None

            else:
                st.warning("Please select an input type")
                return

            # Clear selection button
            if (st.session_state.selected_files or st.session_state.selected_url_file) and st.button("Clear Selection"):
                st.session_state.selected_files = None
                st.session_state.selected_url_file = None
                st.rerun()

    
    # end input_setting_container
        # ---------------
        # Process Images Button
    # ---------------
        process_container = st.container(border=True)
        if True:#st.session_state.files_are_selected_to_process:
            with process_container:
                process_button_col, status_bar_col, pause_button_col = st.columns([1, 4, 1])
                with process_button_col:
                    st.container(height=20, border=False)
                    st.button(
                            "Process Images",
                            on_click=process_images_callback,
                            args=(
                                st.session_state.api_key_dict,
                                prompt_text_from_file,
                                selected_llms,
                                selected_prompt_file,
                                input_type,
                                url_file,
                                local_image_files
                            )
                            )
                with status_bar_col:        
                    status_bar = st.text_area("Status:", st.session_state.status_msg, height=100)
                if st.session_state.pause_button_enabled:
                    with pause_button_col:
                        proceed_option = st.radio("How to Proceeed?:", ["Pause", "Retry Failed and Remaining Jobs", "Finish Remaining Jobs", "Cancel All Jobs", "Cancel All Jobs and Abort Editing"])
                        if proceed_option == "Finish Remaining Jobs":
                            st.session_state.status_msg = "Skipping Failed Jobs and Finishing remaining jobs..."
                            resume_jobs(try_failed_jobs=False)
                        elif proceed_option == "Retry Failed and Remaining Jobs":
                            st.session_state.status_msg = "Retrying Failed Jobs and Finishing remaining jobs..."
                            resume_jobs(try_failed_jobs=True)
                        elif proceed_option == "Cancel all Jobs and Abort Editing":
                            st.session_state.pause_button_enabled = False
                            st.session_state.status_msg = "Cancelling remaining jobs and aborting editing..."
                            reset_states()
                        elif proceed_option == "Cancel All Jobs":
                            st.session_state.pause_button_enabled = False
                            st.session_state.status_msg = "Cancelling remaining jobs..."   
                            


    else:
        if not st.session_state.reedit_mode:
            st.session_state.reedit_mode = True
        load_saved_edits_container = st.container(border=True)     
        with load_saved_edits_container:
            update_overall_session_time()
            loading_option = st.radio("Select Loading Option:", ["Session", "Selected File(s)"])
            if loading_option == "Session":
                session_files = [f for f in os.listdir(f"{TRANCRIPTION_FOLDER}/sessions") if f.endswith(".json")]
                if session_files:
                    sorted_session_files = sort_filenames_by_timestamp(session_files)
                    selected_session_file = st.selectbox("Select Session File:", sorted_session_files)
                    col1, col2 = st.columns(2)
                    with col1:
                        if selected_session_file:
                            if st.button("Load Selected File"):
                                re_edit_session(selected_session_file)
                    with col2:
                        if st.button("Cancel"):
                            st.session_state.reedit_mode = False
                            st.rerun()    
                else:
                    st.warning("No .json files found in the sessions folder.")
                    if st.button("Cancel"):
                        st.session_state.reedit_mode = False
                        st.rerun()
            else:            
                reedit_files = [f for f in os.listdir(f"{TRANCRIPTION_FOLDER}/versions") if f.endswith(".json")]
                if reedit_files:
                    selected_files = st.multiselect("Select Files:", reedit_files)
                    col1, col2 = st.columns(2)
                    with col1:
                        if selected_files:
                            if st.button("Load Selected Files"):
                                re_edit_saved_versions(selected_files)
                    with col2:
                        if st.button("Cancel"):
                            st.session_state.reedit_mode = False
                            st.rerun()
                else:
                    st.warning("No .json files found in the versions folder.")
                    if st.button("Cancel"):
                        st.session_state.reedit_mode = False
                        st.rerun()
            # end load_saved_edits_container
    # ---------------
    # Output Display
    #---------------
    if True:#st.session_state.processed_outputs and st.session_state.processed_images:
        editor_container = st.container(border=False) 
        with editor_container:
            st.write("## Editor")
            col_image, col_field_editor = st.columns([4,3])
            with col_image:
                col_text, col_button = st.columns([2,1])
                with col_text:
                    current_image_idx = st.session_state.current_image_index + 1 if st.session_state.processed_images else 0
                    st.write(f"### Image {current_image_idx}")
                if st.session_state.processed_images:
                    idx = st.session_state.current_image_index
                    image = st.session_state.processed_images[idx]
                    with col_button:
                        st.button("Open Full Screen", on_click=open_fullscreen)
                      
                    st.image(image, caption=None, use_container_width=True)
                    
                    
                      

            with col_field_editor:
                st.container(border=False, height=250)
                if st.session_state.processed_outputs:
                    st.write("https://ipa.typeit.org/full/")
                    st.write("https://translate.google.com/") 
                    content_options = get_content_options()
                    selected_content = st.selectbox("Select Content To View or Edit:", content_options)
                    st.session_state.content_option = "content" if selected_content=="transcript" else selected_content
                    st.session_state.editing_view_option = st.radio("Select Editor View:", ["Fieldname", "Full Text"], index=0)
                    
                    if st.session_state.editing_view_option == "Fieldname":
                        st.container(height=175, border=False)
                        st.session_state.current_transcript_obj = st.session_state.processed_outputs[st.session_state.current_image_index]
                        col_prev_field, col_next_field, __ = st.columns(3)
                        if st.session_state.processed_outputs and st.session_state.processed_images and st.session_state.content_option=="content":
                            
                            with col_next_field:
                                st.button("next field", on_click=go_to_next_field)         
                            with col_prev_field:       
                                st.button("prev field", on_click=go_to_previous_field)
                            st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()
                            st.session_state.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
                            st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
                            emoji = get_validation_rating_with_emoji(st.session_state.current_fieldname)
                            md_fieldname = f"{st.session_state.current_fieldname} {emoji}"
                            st.write(f"#### {md_fieldname}")
                            
                            st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()
                            st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
                            st.session_state.current_fieldvalue = st.session_state.current_output_dict[st.session_state.current_fieldname]["value"]
                            st.session_state.field_text_area = st.text_area("*Press Ctrl+Enter to accept edits*", st.session_state.current_fieldvalue, on_change=update_fieldvalue, key="fieldvalue_key", height=68)
                            
                    else:
                        #st.container(height=500, border=False)
                        text_container = st.container(border=False)
                        with text_container:
                            current_output_dict = st.session_state.current_output_dict
                            output_as_text = dict_to_text(current_output_dict)
                            text_area_height = st.slider("text area height", min_value=100, max_value=600, value=300, label_visibility="collapsed", key="text_area_height")                
                            txt = st.text_area("**Press Ctrl-Enter to Accept Changes**", output_as_text, st.session_state.get("text_area_height", 300), key="text_output_key", on_change=update_text_output)
                                                        
                            js = """
                            <script>
                            const txt_areas = window.parent.document.querySelectorAll('div[data-testid="stTextArea"] textarea');
                            txt_areas.forEach(txt => {
                                txt.spellcheck = false;
                                }
                            );
                            </script>
                            """

                            html(js, height=0)
                            
                    image_ref = st.session_state.current_transcript_obj.image_ref if st.session_state.current_transcript_obj else f"Image {current_image_idx}" 
                    st.write(image_ref)
                    nav_prev, nav_next, notes_opt = st.columns([1,1,2])
                    with nav_prev:
                        st.button("Prev", on_click=go_previous_image)
                    with nav_next:
                        st.button("Next", on_click=go_next_image)
                    with notes_opt:
                        st.button(st.session_state.show_notes_msg, on_click=enable_notes_display)
                else:
                    st.write("No transcription to display.")
        
        # end editor_container
            # ---------------
        # Full-Screen View (if enabled)
        #---------------
        if True:#st.session_state.editing_view_option == "Table":
            table_container = st.container(border=False)
            with table_container:
                current_output_dict = st.session_state.current_output_dict
                fieldnames = [k for k in current_output_dict.keys()]
                if st.session_state.content_option == "content":
                    validation_ratings = [get_validation_rating_with_emoji(fieldname) for fieldname in fieldnames]
                    data = {"fieldname": [], "rating": validation_ratings}
                    column_config={
                                    "value": st.column_config.TextColumn(
                                        "value",
                                        width="large",
                                    ),
                                    "rating": st.column_config.TextColumn(
                                        "rating",
                                        width="small",
                                    )
                                }

                    for fieldname, d in current_output_dict.items():
                        data["fieldname"].append(fieldname)
                        for k, v in d.items():
                            if k in ["notes", "new notes"] and not st.session_state.show_notes:
                                continue
                            if k not in data:
                                data[k] = []
                            data[k].append(v)
                    df = pd.DataFrame(data)
                    ###### slider goes here
                    # Add this right before the data editor
                    
                    
                    # Then modify your data editor to use the slider value
                    edited_df = st.data_editor(
                        df, 
                        use_container_width=True, 
                        column_config=column_config, 
                        hide_index=True, 
                        key="my_key", 
                        height=st.session_state.get('table_height', 225)  # Use the slider value here
                    )
                    table_height = st.slider("table height", min_value=100, max_value=600, value=225, label_visibility="collapsed", key="table_height")
                    edited_elements = st.session_state["my_key"]["edited_rows"]
                elif st.session_state.content_option == "comparisons":
                    current_version = st.session_state.current_transcript_obj.versions[0]
                    print(f"{st.session_state.content_option =}")
                    data = {"fieldname": []}
                    comparisons_dict = current_version["comparisons"]
                    for comparison_name, d in comparisons_dict.items():
                        data["fieldname"] = list(d.keys())
                        for k, v in d.items():
                            if comparison_name not in data:
                                data[comparison_name] = []
                            data[comparison_name].append(v)
                    df = pd.DataFrame(data)
                    edited_df = st.data_editor(
                        df, 
                        use_container_width=True, 
                        hide_index=True
                    )
                else:
                    versions = st.session_state.current_transcript_obj.versions
                    version_names = [v["new version name"] for v in versions]
                    print(f"{st.session_state.content_option =}")
                    data = {"fieldname": []}
                    content_objs = [obj[st.session_state.content_option] for obj in versions]
                    if type(content_objs[0])==dict:# and any(type(val)==dict for val in content_objs[0].values()):
                        for version_name, content_obj in zip(version_names, content_objs):
                            fieldnames = list(content_obj.keys())
                            if len(fieldnames)!=10:
                                continue
                            data["fieldname"] = fieldnames    
                            for k, v in content_obj.items():
                                if version_name not in data:
                                    data[version_name] = []
                                data[version_name].append(v)
                                print(f"{len(data['fieldname']) =}, {len(data[version_name]) = }")
                        df = pd.DataFrame(data)
                        edited_df = st.data_editor(
                            df, 
                            use_container_width=True, 
                            hide_index=True
                        )
                    elif False:#type(content_objs[0])==dict:
                        data["value"] = []
                        for fieldname, val in content_objs[0].items():
                            data["fieldname"].append(fieldname)
                            data["value"].append(val)
                        df = pd.DataFrame(data)
                        edited_df = st.data_editor(
                            df, 
                            use_container_width=True, 
                            hide_index=True
                        )    

        # end table_container        
        # end table_container
        
            
        # ---------------
        # Bottom Buttons
        #---------------
        bottom_buttons_container = st.container(border=True)
        with bottom_buttons_container:
            col_save_table_edits, col_save_text, col_download, col_save_to_json, col_chat_button = st.columns(5)
            if st.session_state.editing_view_option == "Table":
                with col_save_table_edits:
                    st.button("Save Table Changes", on_click=save_table_edits, args=(edited_elements, fieldnames, current_output_dict))
            with col_save_text:
                st.button("Update Text Output", on_click=save_edits_as_text)

            with col_download:
                if st.session_state.processed_outputs:
                    session_filename = f"{st.session_state.user_name}-{get_timestamp()}-session.txt"
                    st.download_button(
                        label="Download Session as TXT",
                        data=st.session_state.final_output,
                        file_name=session_filename,
                        mime="text/plain",
                        help="Save the combined output file to your local machine"
                    )
            with col_save_to_json:
                update_overall_session_time()
                st.button("Save edits to JSON", on_click=save_edits_to_json)
            with col_chat_button:
                msg = "Chat with LLM" if not st.session_state.show_chat_area else "Send Chat"
                st.button(msg, on_click=chat_with_llm)
            col_output, col_chat_area = st.columns(2)
            with col_output:
                st.write("### Final Output (Combined)")
                st.text_area("Combined Output:", st.session_state.final_output, height=600)
            if st.session_state.show_chat_area:           
                with col_chat_area:
                    col_header, col_include = st.columns(2)
                    with col_header:
                        st.write("### Chat Area")
                    with col_include:
                        option = st.radio("Include Image?", ["no", "yes"])
                        st.session_state.include_image = option=="yes"   
                    st.session_state.chat_area = st.text_area("**Be sure to click Ctrl+Enter before clicking Send Chat***", st.session_state.current_chat, height=600)
                    col_close_chat, col_new_chat = st.columns(2)
                    with col_close_chat:
                        st.button("Close Chat", on_click=close_chat)
                    with col_new_chat:
                        st.button("New Chat", on_click=new_chat)   
        # end bottom_buttons_container
            
    else:
        st.write("No transcription to display.")    
    if st.session_state.fullscreen and st.session_state.processed_images:
        show_fullscreen_image()

    


if __name__ == "__main__":
    main()
# version_name = create_version(created_by=self.modelname, content=transcription_dict, costs=transcript_processing_data, is_ai_generated=True, old_version_name=old_version_name, editing = {}, new_notes = {})