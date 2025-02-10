import streamlit as st
import os
import queue
from datetime import datetime
from PIL import Image
from io import BytesIO
from llm_interfaces.transcript import Transcript
from llm_interfaces.utility import extract_info_from_text
import time
import json
import re

# Replace with your real processor classes if you want
#from processors.claude_url import ClaudeImageProcessorThread
from llm_interfaces.claude_interface import ClaudeImageProcessorThread
from processors.gpt_url import GPTImageProcessorThread
from processors.claude_local import ClaudeLocalImageProcessorThread
from processors.gpt_local import GPTLocalImageProcessorThread

PROMPT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

def main():
    st.set_page_config(page_title="Herbarium Parser (Callbacks, with Model & Prompt in Output)", layout="wide")

    # ---------------------
    # Session State Setup
    # ---------------------
    if "processed_images" not in st.session_state:
        st.session_state.processed_images = []
    if "processed_outputs" not in st.session_state:
        st.session_state.processed_outputs = []
    if "processed_versions" not in st.session_state:
        st.session_state.processed_versions = []   
    if "processed_urls" not in st.session_state:
        st.session_state.processed_urls = []        
    if "current_image_index" not in st.session_state:
        st.session_state.current_image_index = 0
    if "final_output" not in st.session_state:
        st.session_state.final_output = ""
    if "urls" not in st.session_state:
        st.session_state.urls = []
    if "prompt_text" not in st.session_state:
        st.session_state.prompt_text = ""
    if "local_images" not in st.session_state:
        st.session_state.local_images = []
    if "fullscreen" not in st.session_state:
        st.session_state.fullscreen = False
    # NEW: Store chosen LLM + prompt name for final output/filename
    if "selected_llm" not in st.session_state:
        st.session_state.selected_llm = ""
    if "selected_prompt" not in st.session_state:
        st.session_state.selected_prompt = ""
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "session_name" not in st.session_state:
        st.session_state.session_name = ""
    if "session_folder" not in st.session_state:
        st.session_state.session_folder = "single_transcriptions/" 
    if "filename_to_edit" not in st.session_state:
        st.session_state.filename_to_edit = ""               

    st.write("## Enter User Name")
    st.session_state.user_name = st.text_input("Enter your name:", value=st.session_state.user_name)
    set_session_name()
    print(f"{st.session_state.session_name = }")
    # ---------------
    # Prompt Selection
    # ---------------
    st.write("## Prompt Selection")
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

    # ---------------
    # Input Settings
    # ---------------
    st.write("## Input Settings")

    # LLM Choice
    llm_options = ["Claude 3.5 Sonnet", "GPT-4o"]
    selected_llm = st.selectbox("Select LLM:", llm_options, index=0)

    # API key file
    api_key_file = st.file_uploader("Upload API Key File (TXT)", type=["txt"])

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

    # ---------------
    # Process Images Button
    # ---------------
    col_process, col_re_edit = st.columns(2)
    with col_process:
        st.button(
            "Process Images",
            on_click=process_images_callback,
            args=(
                api_key_file,
                prompt_text_from_file,
                selected_llm,
                selected_prompt_file,
                input_type,
                url_file,
                local_image_files
            )
        )

    with col_re_edit:
        st.button(
            "Re-Edit Latest Version",
            on_click=re_edit_callback,
        )

    # ---------------
    # Output Display
    #---------------
    col1, col2 = st.columns([1, 2])

    with col1:
        st.write("### Image Preview")
        if st.session_state.processed_images:
            idx = st.session_state.current_image_index
            image = st.session_state.processed_images[idx]
            st.image(image, caption=f"Image {idx+1}", use_container_width=True)
            st.button("Open Full Screen", on_click=open_fullscreen)
        else:
            st.write("No processed images to display.")

        # Navigation
        nav_prev, nav_next = st.columns(2)
        with nav_prev:
            st.button("Previous", on_click=go_previous)
        with nav_next:
            st.button("Next", on_click=go_next)

    with col2:
        st.write("### Extracted/Parsed Text")
        if st.session_state.processed_outputs and st.session_state.processed_images:
            current_output = st.session_state.processed_outputs[st.session_state.current_image_index]
        else:
            current_output = ""
        st.write("https://ipa.typeit.org/full/") 
        st.write("https://translate.google.com/")   

    # ---------------
    # Full-Screen View (if enabled)
    #---------------
    if st.session_state.fullscreen and st.session_state.processed_images:
        show_fullscreen_image()

    # ---------------
    # Bottom Buttons
    #---------------
    col_save, col_download, col_save_to_json = st.columns(3)

    with col_save:
        st.button("Save Edits in Memory", on_click=save_edits)

    with col_download:
        # Build a filename containing model name and prompt
        # Replace spaces or special chars if desired
        model_short = st.session_state.selected_llm.replace(" ", "_")
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
        st.button("Save edits to JSON", on_click=save_edits_to_json)

    st.write("### Final Output (Combined)")
    st.text_area("Combined Output:", st.session_state.final_output, height=600)


# ----------------
# Callback Functions
# ----------------

# session state functions

def set_session_name():
    timestamp = get_timestamp() 
    st.session_state.session_name = f"{st.session_state.user_name}-{timestamp}" 

def get_timestamp():
    return  time.strftime("%Y-%m-%d-%H%M-%S")        

# file handling callbacks

def save_edits_to_json():
    for output, version_name, url in zip(st.session_state.processed_outputs, st.session_state.processed_versions, st.session_state.processed_urls):
        transcript = Transcript(url, st.session_state.selected_prompt)
        transciption_dict = extract_info_from_text(output)
        costs = get_costs()
        transcript.create_version(created_by=st.session_state.user_name, content=transciption_dict, data=costs, old_version_name=version_name)


# editing callbacks

def re_edit_callback():
    st.write("## Re-Edit File Selection")
    reedit_files = [f for f in os.listdir(st.session_state.session_folder) if f.endswith(".json")]

    if reedit_files:
        selected_reedit_file = st.selectbox("Select a File:", reedit_files)
        with open(os.path.join(st.session_state.session_folder, selected_reedit_file), "r", encoding="utf-8") as rf:
            reedit_file = json.load(rf)
            print(f"{reedit_file = }")
    else:
        st.warning("No .json prompt files found in the session folder.")

# version handling callbacks

# version creation/editing callbacks

def get_costs():
        return {
            "input tokens": 0,
            "output tokens": 0,
            "input cost $": 0,
            "output cost $": 0
        }

# formatting strings
# color keys red using CSS
def color_keys(text):
    text = re.sub(r'(\w+):', r'<span style="color: red">\1:</span>', text)
    return text








def process_images_callback(
    api_key_file,
    prompt_text_from_file,
    selected_llm,
    selected_prompt_file,
    input_type,
    url_file,
    local_image_files
):
    """
    Callback to process images. No st.experimental_rerun() needed:
    changing session state triggers re-run automatically.
    """
    if not api_key_file:
        st.error("Please upload the API key file.")
        return
    if not prompt_text_from_file:
        st.error("No prompt text available (folder empty or file missing).")
        return

    try:
        api_key = api_key_file.read().decode("utf-8").strip()
    except:
        st.error("Unable to read API key file. Check encoding or file format.")
        return

    # Store the chosen model & prompt in session for final output/filename
    st.session_state.selected_llm = selected_llm
    st.session_state.selected_prompt = selected_prompt_file

    # Reset states
    st.session_state.prompt_text = prompt_text_from_file
    st.session_state.processed_images.clear()
    st.session_state.processed_outputs.clear()
    st.session_state.processed_versions.clear()
    st.session_state.processed_urls.clear()
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

        # Pick processor
        if selected_llm == "Claude 3.5 Sonnet":
            processor_thread = ClaudeImageProcessorThread(api_key, st.session_state.selected_prompt, st.session_state.prompt_text, urls, result_queue)
        else:
            processor_thread = GPTImageProcessorThread(api_key, st.session_state.prompt_text, urls, result_queue)

        processor_thread.process_images()

    else:
        # Local images
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

        if selected_llm == "Claude 3.5 Sonnet":
            processor_thread = ClaudeLocalImageProcessorThread(api_key, st.session_state.prompt_text, local_images_list, result_queue)
        else:
            processor_thread = GPTLocalImageProcessorThread(api_key, st.session_state.prompt_text, local_images_list, result_queue)

        processor_thread.process_images()

    # Retrieve results
    while True:
        try:
            image, output, version_name, url = result_queue.get_nowait()
        except queue.Empty:
            break
        if image is None and output is None and version_name is None:
            break
        if image:
            st.session_state.processed_images.append(image)
        st.session_state.processed_outputs.append(output)
        st.session_state.processed_versions.append(version_name)
        st.session_state.processed_urls.append(url)
        st.session_state.final_output += output + "\n" + ("=" * 50) + "\n"

    if st.session_state.processed_images:
        st.success("Images processed successfully!")
    else:
        st.warning("No images or errors occurred. Check logs or outputs.")


def open_fullscreen():
    """Callback to switch 'fullscreen' on."""
    st.session_state.fullscreen = True

def close_fullscreen():
    """Callback to switch 'fullscreen' off."""
    st.session_state.fullscreen = False

def go_previous():
    """
    Moves to the previous image, if possible.
    Saves current text from output_text_area into the session.
    """
    if st.session_state.current_image_index > 0:
        save_current_output_in_session()
        st.session_state.current_image_index -= 1

def go_next():
    """
    Moves to the next image, if possible.
    Saves current text from output_text_area into the session.
    """
    if st.session_state.current_image_index < len(st.session_state.processed_images) - 1:
        save_current_output_in_session()
        st.session_state.current_image_index += 1

def save_edits():
    """
    Saves the current text and rebuilds the final_output from processed_outputs,
    *then* prepends a small header with model + prompt used.
    """
    if st.session_state.processed_outputs and st.session_state.processed_images:
        save_current_output_in_session()

    # Rebuild final_output from all processed outputs
    combined_text = ""
    for out in st.session_state.processed_outputs:
        combined_text += out + "\n" + ("=" * 50) + "\n"

    # Prepend a short header with model + prompt
    model_info = f"Model used: {st.session_state.selected_llm}\n"
    prompt_info = f"Prompt used: {st.session_state.selected_prompt}\n\n"
    final_text = model_info + prompt_info + combined_text

    st.session_state.final_output = final_text
    st.success("Edits + header saved in memory! You can now download below.")

def save_current_output_in_session():
    """
    Helper: saves text area changes to st.session_state.processed_outputs.
    """
    if "processed_outputs" in st.session_state and "output_text_area" in st.session_state:
        idx = st.session_state.current_image_index
        if idx < len(st.session_state.processed_outputs):
            st.session_state.processed_outputs[idx] = st.session_state.output_text_area

            

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

if __name__ == "__main__":
    main()
