import streamlit as st
import os
import queue
from datetime import datetime
from PIL import Image
from io import BytesIO
import requests
from llm_processing.transcript2 import Transcript
from llm_processing.utility import extract_info_from_text
import time
import json
import re

from llm_processing.llm_manager2 import ProcessorManager
from llm_processing.claude_interface2 import ClaudeImageProcessorThread

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
    # outputs    
    #### elements in st.session_state.processed_outputs elements
    if "processed_images" not in st.session_state:
        st.session_state.processed_images = []
    if "processed_outputs" not in st.session_state:
        st.session_state.processed_outputs = []
    if "processed_version_names" not in st.session_state:
        st.session_state.processed_version_names = []   
    if "processed_image_refs" not in st.session_state:
        st.session_state.processed_image_refs = []
    #### editing output
    if "current_full_edits" not in st.session_state:
        st.session_state.current_full_edits = ""
    if "editing_data" not in st.session_state:
        st.session_state.editing_data = []

    if "final_output" not in st.session_state:
        st.session_state.final_output = ""
    if "chat_area" not in st.session_state:
        st.session_state.chat_area = st.empty()
    if "include_image" not in st.session_state:
        st.session_state.include_image = False             
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
    if "current_version_name" not in st.session_state:
        st.session_state.current_version_name = ""

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
    # processing
    st.session_state.current_output_dict.clear()
    st.session_state.filename_to_edits.clear()
    st.session_state.session_to_edit = ""
    st.session_state.fieldnames.clear() 
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
    st.session_state.current_version_name = ""
    st.session_state.chat_history = ""
    st.session_state.show_chat_area = False
    st.session_state.current_chat = ""

def reset_processed_elements():
    st.session_state.processed_images.clear()
    st.session_state.processed_outputs.clear()
    st.session_state.processed_version_names.clear()
    st.session_state.processed_image_refs.clear()



# ----------------
# Callback and Support Functions
# ----------------

def append_processed_elements(image, transcript_obj, version_name, image_ref):
    st.session_state.processed_images.append(image)
    st.session_state.processed_outputs.append(transcript_obj)
    st.session_state.processed_version_names.append(version_name)
    st.session_state.processed_image_refs.append(image_ref)
    output_dict = transcript_obj.get_version_by_name(version_name)["content"]
    st.session_state.final_output += image_ref + "\n" + dict_to_text(output_dict) + "\n" + ("=" * 50) + "\n"
    editing_data = {"costs": get_costs_blank_dict(), "editing": get_editing_blank_dict()}
    st.session_state.editing_data.append(editing_data)

def chat_with_llm():
    if not st.session_state.show_chat_area:
        st.session_state.chat_area.empty()
        st.session_state.current_chat = f"{st.session_state.user_name}: "
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
                    print(f"returning after yes")
                    return
                    image_ref = st.session_state.current_transcript_obj.image_ref
                    response, costs = processor.chat(new_message, image_ref)
                else:
                    print(f"returning after no")
                    return
                    response, costs = processor.chat(new_message)
                update_costs(costs)
                st.session_state.chat_history = f"{current_chat}\n\nAssistant: {response}\n{st.session_state.user_name}: "
                update_editing({"chats": st.session_state.chat_history})
                st.session_state.current_chat = st.session_state.chat_history
            except Exception as e:
                st.error(f"Error processing chat: {str(e)}")


def color_keys(fieldname):
    if st.session_state.content_option != "content":
        return f":blue[{st.session_state.current_fieldname}]"
    filename = st.session_state.current_transcript_obj.get_legal_json_filename()
    rating = st.session_state.current_transcript_obj.get_field_validation_rating(fieldname, st.session_state.current_version_name)
    return f":red[{st.session_state.current_fieldname}]" if rating==0 else f":orange[{st.session_state.current_fieldname}]" if rating==1 else f":blue[{st.session_state.current_fieldname}]" if rating==2 else f":green[{st.session_state.current_fieldname}]" if rating ==3 else fieldname

def close_chat():
    """Callback to switch 'show_chat_area' off."""
    st.session_state.show_chat_area = False
    new_chat()

def close_fullscreen():
    """Callback to switch 'fullscreen' off."""
    st.session_state.fullscreen = False

def dict_to_text(d):
    return "\n".join([f"{k}: {v}" for k, v in d.items()]) + 8*"\n"

def get_content_options():
    if st.session_state.current_transcript_obj:
        version_name = st.session_state.current_transcript_obj.get_latest_version_name()
        st.session_state.current_version_name = version_name
        options = list(st.session_state.current_transcript_obj.versions[st.session_state.current_version_name].keys())
        return [o if o != "content" else "transcript" for o in options ]
    else:
        return ["transcript"]
        
def get_costs_blank_dict():
        return {
            "input tokens": 0,
            "output tokens": 0,
            "input cost $": 0,
            "output cost $": 0
        }

def get_current_version_name():
    return st.session_state.processed_outputs[st.session_state.current_image_index].get_latest_version_name()

def get_editing_blank_dict():
    return {"time started": 0, "time editing": 0, "chats": ""}    

def get_legal_json_filename(image_ref):
        ref = re.sub(r"[\/]", "#", image_ref)
        ref = re.sub(r"[:]", "$", ref)
        ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
        filename = f"{TRANCRIPTION_FOLDER}/transcripts/{ref}-transcript.json" 
        return filename 

def get_option_dict_from_version_in_processed_outputs():
    return st.session_state.processed_outputs[st.session_state.current_image_index].versions[st.session_state.current_version_name][st.session_state.content_option]

def get_timestamp():
    return  time.strftime("%Y-%m-%d-%H%M-%S")

def get_val_from_version_in_processed_outputs():
    return st.session_state.processed_outputs[st.session_state.current_image_index].versions[st.session_state.current_version_name][st.session_state.content_option][st.session_state.current_fieldname]

def go_next_image():
    """
    Moves to the next image, if possible.
    Saves current text from output_text_area into the session.
    """
    if st.session_state.processed_outputs and st.session_state.processed_images:
        update_time_to_edit(start=False)
        # Save current field value before moving
        st.session_state.current_output_dict[st.session_state.current_fieldname] = st.session_state.field_text_area
        update_version_in_processed_outputs(st.session_state.field_text_area)
        update_processed_outputs()
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
        # Save current field value before moving
        st.session_state.current_output_dict[st.session_state.current_fieldname] = st.session_state.field_text_area
        update_version_in_processed_outputs(st.session_state.field_text_area)
        update_processed_outputs()
        if st.session_state.current_image_index > 0:
            st.session_state.current_image_index -= 1
        else:
            st.session_state.current_image_index = len(st.session_state.processed_images) - 1
        update_displays()
        update_time_to_edit(start=True)

def go_to_next_field():
    save_field_text_area()
    if st.session_state.field_idx == len(st.session_state.fieldnames) - 1:
        st.session_state.field_idx = 0
    else:
        st.session_state.field_idx += 1
    update_time_to_edit(start=False)
    

def go_to_previous_field():
    save_field_text_area()
    if st.session_state.field_idx == 0:
        st.session_state.field_idx = len(st.session_state.fieldnames) - 1
    else:
        st.session_state.field_idx -= 1
    update_time_to_edit(start=False)    

def new_chat():
    st.session_state.chat_history = ""
    st.session_state.chat_area = st.empty()
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
    """
    Callback to process images. No st.experimental_rerun() needed:
    changing session state triggers re-run automatically.
    """
    for llm in selected_llms:
        if not api_key_dict[llm]:
            st.error(f"Please upload the API key file for {llm}.")
            return
    if not prompt_text_from_file:
        st.error("No prompt text available (folder empty or file missing).")
        return
    for llm in selected_llms:
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
    result_queue = queue.Queue()
    # Decide URL-based or local
    if input_type == "URL List":
        if not url_file:
            st.error("Please upload a .txt file containing image URLs.")
            return
        try:
            urls_content = url_file.read().decode("utf-8")
            urls = urls_content.strip().splitlines()
        except:
            st.error("Unable to read URL file. Check encoding or file format.")
            return
        st.session_state.urls = urls
        processor_manager = ProcessorManager(api_key_dict, selected_llms, st.session_state.selected_prompt, st.session_state.prompt_text, urls, result_queue)
        processor_manager.process_images()
    else:
        if not local_image_files:
            st.error("Please upload at least one image file.")
            return
        local_images_list = []
        for uploaded_file in local_image_files:
            try:
                image = Image.open(uploaded_file)
                local_images_list.append((image, uploaded_file.name))
            except Exception as e:
                st.warning(f"Could not open {uploaded_file.name}: {e}")
        st.session_state.local_images = local_images_list
        processor_manager = ProcessorManager(api_key_dict, selected_llms, st.session_state.selected_prompt, st.session_state.prompt_text, local_images_list, result_queue)
        processor_manager.process_images()
    # Retrieve results
    while True:
        try:
            image, transcript_obj, version_name, image_ref = result_queue.get_nowait()
        except queue.Empty:
            break
        if image is None and transcript_obj is None and version_name is None:
            break
        append_processed_elements(image, transcript_obj, version_name, image_ref)
        st.session_state.processed_images.append(image)
        st.session_state.processed_outputs.append(transcript_obj)
        st.session_state.processed_version_names.append(version_name)
        st.session_state.processed_image_refs.append(image_ref)
        output_dict = transcript_obj.get_version_by_name(version_name)["content"]
        st.session_state.final_output += image_ref + "\n" + dict_to_text(output_dict) + "\n" + ("=" * 50) + "\n"
        editing_data = {"costs": get_costs_blank_dict(), "editing": get_editing_blank_dict()}
        st.session_state.editing_data.append(editing_data)

    if st.session_state.processed_images:
        st.success("Images processed successfully!")
    else:
        st.warning("No images or errors occurred. Check logs or outputs.")
    update_overall_session_time()    

def re_edit_saved_versions(selected_reedit_files):
    """Handle loading the selected file"""
    save_edits_to_json()
    reset_processed_elements()
    reset_states()
    try:
        for selected_file in selected_reedit_files:
            with open(os.path.join(f"{TRANCRIPTION_FOLDER}/versions", selected_file), "r", encoding="utf-8") as rf:
                transcript_dict = json.load(rf)
                latest_version_name = [k for k in transcript_dict.keys()][0]
                latest_version_dict = transcript_dict[latest_version_name]
                image_ref = latest_version_dict["data"]["image ref"]
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
        st.session_state.current_image_index = 0
        st.session_state.current_version_name = latest_version_name
        st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()

        st.session_state.current_transcript_obj = transcript_obj
        st.session_state.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
        st.session_state.field_idx = 0
        st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
        st.session_state.current_fieldvalue = st.session_state.current_output_dict[st.session_state.current_fieldname]            
    except Exception as e:
            st.error(f"Error loading file: {str(e)}")
    st.session_state.reedit_mode = False
    #st.rerun() 
    #       
def re_edit_session(selected_session_file):
    """Handle loading the selected file"""
    save_edits_to_json()
    reset_processed_elements()
    reset_states()
    try:
        with open(os.path.join(f"{TRANCRIPTION_FOLDER}/sessions", selected_session_file), "r", encoding="utf-8") as rf:
            session_dict = json.load(rf)
            for image_ref, transcript_dict in session_dict.items():
                latest_version_name = [k for k in transcript_dict.keys()][0]
                latest_version_dict = transcript_dict[latest_version_name]
                image_ref = latest_version_dict["data"]["image ref"]
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
        st.session_state.current_image_index = 0
        st.session_state.current_version_name = latest_version_name
        st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()

        st.session_state.current_transcript_obj = transcript_obj
        st.session_state.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
        st.session_state.field_idx = 0
        st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
        st.session_state.current_fieldvalue = st.session_state.current_output_dict[st.session_state.current_fieldname]            
    except Exception as e:
            st.error(f"Error loading file: {str(e)}")
    st.session_state.reedit_mode = False
    #st.rerun()       

    
def save_current_output_in_session():
    """
    Helper: saves text area changes to st.session_state.processed_outputs.
    """
    if "processed_outputs" in st.session_state and "output_text_area" in st.session_state:
        idx = st.session_state.current_image_index
        if idx < len(st.session_state.processed_outputs):
            st.session_state.processed_outputs[idx][[st.session_state.content_option]] = extract_info_from_text(st.session_state.output_text_area)

def save_edits():
    update_overall_session_time()
    """
    Saves the current text and rebuilds the final_output from processed_outputs,
    *then* prepends a small header with model + prompt used.
    """
    if st.session_state.processed_outputs and st.session_state.processed_images:
        save_current_output_in_session()

    # Rebuild final_output from all processed outputs
    combined_text = ""
    for out, version_name in zip(st.session_state.processed_outputs, st.session_state.processed_version_names):
        output_dict = out.get_version_by_name(version_name)["content"]
        combined_text += dict_to_text(output_dict) + "\n" + ("=" * 50) + "\n"

    # Prepend a short header with model + prompt
    model_info = f"Model(s) used: {st.session_state.selected_llms}\n"
    prompt_info = f"Prompt used: {st.session_state.selected_prompt}\n\n"
    final_text = model_info + prompt_info + combined_text

    st.session_state.final_output = final_text
    st.success("Edits + header saved in memory! You can now download below.")
    
def save_edits_to_json():
    update_overall_session_time()
    update_processed_outputs()
    session_output_dict = {}
    for transcript_obj, version_name, image_ref, editing_data in zip(st.session_state.processed_outputs, st.session_state.processed_version_names, st.session_state.processed_image_refs, st.session_state.editing_data):
        transcript = Transcript(image_ref, st.session_state.selected_prompt)
        costs = editing_data["costs"]
        editing = editing_data["editing"]
        output_dict = transcript_obj.versions[version_name]["content"]
        save_to_json(output_dict, image_ref)
        transcript.create_version(created_by=st.session_state.user_name, content=output_dict, data=costs, is_user=True, old_version_name=version_name, editing=editing)
        session_output_dict[image_ref] = transcript.versions
    session_filename = f"{TRANCRIPTION_FOLDER}/sessions/{st.session_state.user_name}-{get_timestamp()}-session.json"
    with open(session_filename, 'w', encoding='utf-8') as f:
        json.dump(session_output_dict, f, ensure_ascii=False, indent=4)    

def save_field_text_area():
    if st.session_state.processed_outputs and st.session_state.processed_images and st.session_state.content_option=="content":
        st.session_state.current_output_dict[st.session_state.current_fieldname] = st.session_state.field_text_area
        update_version_in_processed_outputs(st.session_state.field_text_area)

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

def update_costs(new_costs: dict):
    if st.session_state.processed_outputs:
        old_costs = st.session_state.editing_data[st.session_state.current_image_index]["costs"]
        for cost_name, val in new_costs.items():
            old_costs[cost_name] += val

def update_displays():
    st.session_state.current_transcript_obj = st.session_state.processed_outputs[st.session_state.current_image_index]
    transcript_dict = st.session_state.current_transcript_obj.versions
    version_name = [k for k in transcript_dict.keys()][0]
    st.session_state.current_version_name = version_name
    st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()
    st.session_state.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
    st.session_state.field_idx = 0
    if st.session_state.content_option=="content":
        st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
        st.session_state.current_fieldvalue = st.session_state.current_output_dict[st.session_state.current_fieldname] 
                   
def update_editing(new_notes: dict):
    if st.session_state.processed_outputs:
        old_notes = st.session_state.editing_data[st.session_state.current_image_index]["editing"]
        for note_name, val in new_notes.items():
            old_notes[note_name] += val  

def update_overall_session_time():
    st.session_state.overall_session_time = time.time() - st.session_state.session_start_time

def update_time_to_edit(start=True):
    update_overall_session_time()
    if st.session_state.processed_outputs:
        old_notes = st.session_state.editing_data[st.session_state.current_image_index]["editing"]
        start_time = get_timestamp() if start else old_notes["time started"] 
        new_editing_time = time.time() - time.mktime(time.strptime(start_time, "%Y-%m-%d-%H%M-%S"))
        old_notes["time started"] = start_time
        old_notes["time editing"] += new_editing_time

def update_version_in_processed_outputs(val):
    if st.session_state.content_option=="content":
        st.session_state.processed_outputs[st.session_state.current_image_index].versions[st.session_state.current_version_name][st.session_state.content_option][st.session_state.current_fieldname] = val

def update_processed_outputs():
    if st.session_state.content_option=="content" and st.session_state.processed_outputs:
        full_output_dict = extract_info_from_text(st.session_state.current_full_edits)
        st.session_state.processed_outputs[st.session_state.current_image_index].versions[st.session_state.current_version_name][st.session_state.content_option] = full_output_dict    

def main():
    st.set_page_config(page_title="Herbarium Parser (Callbacks, with Model & Prompt in Output)", layout="wide")
    
    st.markdown("""
        <style>
        div.stButton > button {
            background-color: #E0E0E0 ;
        }
        [data-testid="stHorizontalBlock"] {
            background-color: #FFFDD0 !important;  /* Added !important */
            padding: .5rem !important;
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

            # API key file
            api_key_dict = {}
            for llm in selected_llms:
                api_key_dict[llm] = st.file_uploader(f"Upload API Key File For {llm} (TXT)", type=["txt"])
            st.session_state.api_key_dict = api_key_dict
            # Radio for "Local Images" vs. "URL List"
            input_type = st.radio("Select Image Input Type:", ["URL List", "Local Images"], index=0)

            # File uploaders
            if input_type == "URL List":
                url_file = st.file_uploader("Upload URL File (TXT)", type=["txt"])
                local_image_files = None
            else:
                url_file = None
                local_image_files = st.file_uploader(
                    "Upload One or More Images",
                    type=["png", "jpg", "jpeg"],
                    accept_multiple_files=True
                )
        # end input_setting_container
        # ---------------
        # Process Images Button
    # ---------------
        st.button(
                "Process Images",
                on_click=process_images_callback,
                args=(
                    api_key_dict,
                    prompt_text_from_file,
                    selected_llms,
                    selected_prompt_file,
                    input_type,
                    url_file,
                    local_image_files
                )
            )
    else:
        if not st.session_state.reedit_mode:
            st.session_state.reedit_mode = True
        load_saved_edits_container = st.container(border=True)     
        with load_saved_edits_container:
            update_overall_session_time()
            loading_option = st.radio("Select Loading Option:", ["Session", "Selected File(s)"])
            #st.button("Load Latest Versions", on_click=lambda: setattr(st.session_state, 'reedit_mode', True))
            if loading_option == "Session":
                session_files = [f for f in os.listdir(f"{TRANCRIPTION_FOLDER}/sessions") if f.endswith(".json")]
                if session_files:
                    selected_session_file = st.selectbox("Select Session File:", session_files)
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
    if st.session_state.processed_outputs and st.session_state.processed_images:
        editor_container = st.container(border=True) 
        with editor_container:
            st.write("## Editor")
            col1, col2 = st.columns(2)
            with col1:
                col_text, col_button = st.columns([2,1])
                with col_text:
                    current_image_idx = st.session_state.current_image_index + 1 if st.session_state.processed_images else 0
                    st.write(f"### Image {current_image_idx}")
                if st.session_state.processed_images:
                    idx = st.session_state.current_image_index
                    image = st.session_state.processed_images[idx]
                    with col_button:
                        st.button("Open Full Screen", on_click=open_fullscreen)
                    image_ref = st.session_state.current_transcript_obj.image_ref if st.session_state.current_transcript_obj else f"Image {current_image_idx}"   
                    st.image(image, caption=image_ref, use_container_width=True)
                else:
                    st.write("No processed images to display.")

            with col2:
                nav_prev, nav_next = st.columns(2)
                with nav_prev:
                    st.button("Previous", on_click=go_previous_image)
                with nav_next:
                    st.button("Next", on_click=go_next_image)
                content_opt, __ = st.columns(2)    
                with content_opt:
                    content_options = get_content_options()
                    selected_content = st.selectbox("Select Content To View or Edit:", content_options)
                    st.session_state.content_option = "content" if selected_content=="transcript" else selected_content
                    if st.session_state.processed_outputs:
                        st.session_state.current_transcript_obj = st.session_state.processed_outputs[st.session_state.current_image_index]
                        st.session_state.current_version_name = get_current_version_name()   
                if st.session_state.processed_outputs and st.session_state.current_version_name:
                    st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()
                    output_as_text = dict_to_text(st.session_state.current_output_dict)
                    update_time_to_edit(start=True)
                    st.session_state.current_full_edits = st.text_area("*Press Ctrl+Enter to accept edits*", output_as_text, height=425)
                else:    
                    st.session_state.current_full_edits = st.text_area("*Press Ctrl+Enter to accept edits*", "no processed outputs to display", height=425)
                col_prev_field, col_next_field, col_fieldname = st.columns([1,1,5])
                if st.session_state.processed_outputs and st.session_state.processed_images and st.session_state.current_version_name and st.session_state.content_option=="content":
                    with col_fieldname:
                        st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()
                        st.session_state.fieldnames = [k for k in st.session_state.current_output_dict.keys()]
                        st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
                        colored_fieldname = color_keys(st.session_state.current_fieldname)
                        st.write(f"### {colored_fieldname}")
                    with col_next_field:
                        st.button("next", on_click=go_to_next_field)         
                    with col_prev_field:       
                        st.button("prev", on_click=go_to_previous_field)
                    st.session_state.current_output_dict = get_option_dict_from_version_in_processed_outputs()
                    st.session_state.current_fieldname = st.session_state.fieldnames[st.session_state.field_idx]
                    st.session_state.current_fieldvalue = st.session_state.current_output_dict[st.session_state.current_fieldname]
                    st.session_state.field_text_area = st.text_area("*Press Ctrl+Enter to accept edits*", st.session_state.current_fieldvalue, height=75)
                    col_link1, col_link2 = st.columns(2)
                    with col_link1:
                        st.write("https://ipa.typeit.org/full/")
                    with col_link2:
                        st.write("https://translate.google.com/")
                else:
                    st.write("No transcription to display.")       
        # end editor_container
            # ---------------
        # Full-Screen View (if enabled)
        #---------------
        if st.session_state.fullscreen and st.session_state.processed_images:
            show_fullscreen_image()

        # ---------------
        # Bottom Buttons
        #---------------
        bottom_buttons_container = st.container(border=False)
        with bottom_buttons_container:
            col_save, col_download, col_save_to_json, col_chat_button = st.columns(4)

            with col_save:
                st.button("Save Edits in Memory", on_click=save_edits)

            with col_download:
                # Build a filename containing model name and prompt
                # Replace spaces or special chars if desired
                if st.session_state.selected_llms and st.session_state.selected_prompt:
                    model_short = st.session_state.selected_llms[-1].replace(" ", "_")
                    prompt_short = st.session_state.selected_prompt.replace(" ", "_").replace(".txt", "")
                    timestamp_str = datetime.now().strftime("%m_%d_%y-%I_%M%p")

                    out_filename = f"Transcription_{model_short}_{prompt_short}_{timestamp_str}.txt"

                    st.download_button(
                        label="Download Output",
                        data=st.session_state.final_output,
                        file_name=out_filename,
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
        


if __name__ == "__main__":
    main()
