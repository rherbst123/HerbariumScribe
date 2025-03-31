import streamlit as st
import os
from datetime import datetime
from PIL import Image
from io import BytesIO
import requests
import time
import json
import re
import pandas as pd
from dotenv import load_dotenv
from streamlit.components.v1 import html

from llm_processing.llm_manager4 import ProcessorManager
from llm_processing.claude_interface3 import ClaudeImageProcessor
from llm_processing.transcript6 import Transcript
from llm_processing.utility import extract_info_from_text
from llm_processing.session2 import Session
from llm_processing.volume import Volume

# Constants
ENV_FILE = ".env"
REQUIRED_ENV_VARS = {
    "ANTHROPIC_API_KEY": "API key for chat features",
    "OPENAI_API_KEY": "Optional OpenAI API key"
}

PROMPT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
TRANCRIPTION_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

def set_up():
    #if "session_obj" not in st.session_state:
    #    st.session_state.session_obj = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = ""
    if "show_chat_area" not in st.session_state:
        st.session_state.show_chat_area = False            
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = ""
    if "status_msg" not in st.session_state:
        st.session_state.status_msg = ""
    if "pause_button_enabled" not in st.session_state:
        st.session_state.pause_button_enabled = False
    if "pause_button_option" not in st.session_state:
        st.session_state.pause_button_option = ""    
    #### editing output
    if "editor_enabled " not in st.session_state:    
        st.session_state.editor_enabled = False
    if "editing_view_option" not in st.session_state:
        st.session_state.editing_view_option = ""
    if "edited_elements" not in st.session_state:
        st.session_state.edited_elements = {} 
    if "chat_area" not in st.session_state:
        st.session_state.chat_area = ""
    if "include_image" not in st.session_state:
        st.session_state.include_image = False
    if "show_notes" not in st.session_state:
        st.session_state.show_notes = False
    if "show_notes_msg" not in st.session_state:
        st.session_state.show_notes_msg = "Show Notes"               
    if "reedit_mode" not in st.session_state:
        st.session_state.reedit_mode = False
    if "fullscreen" not in st.session_state:
        st.session_state.fullscreen = False
    if "table_type" not in st.session_state:
        st.session_state.table_type = "page"    

def reset_states():
    st.session_state.editor_enabled = False
    st.session_state.show_notes = False
    st.session_state.show_notes_msg = "Show Notes"
    st.session_state.editing_view_option = ""
    st.session_state.edited_elements = {}
    # processing
    # modes
    st.session_state.fullscreen = False
    st.session_state.reedit_mode = False
    st.session_state.chat_history = ""
    st.session_state.show_chat_area = False
    st.session_state.current_chat = ""

# ----------------
# Callback and Support Functions
# ----------------

def chat_with_llm():
    if not st.session_state.show_chat_area:
        st.session_state.chat_area = ""
        st.session_state.current_chat = f"claude-3.5-sonnet is available to answer queries. What is your question?\n\n{st.session_state.session_obj.user_name}: "
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
                st.session_state.chat_history = f"{current_chat}\n\nAssistant: {response}\n\n{st.session_state.session_obj.user_name}: "
                st.session_state.session_obj.update_editing({"chats": st.session_state.chat_history})
                st.session_state.current_chat = st.session_state.chat_history
            except Exception as e:
                st.error(f"Error processing chat: {str(e)}")

def close_chat():
    """Callback to switch 'show_chat_area' off."""
    st.session_state.show_chat_area = False
    new_chat()

def close_fullscreen():
    """Callback to switch 'fullscreen' off."""
    st.session_state.fullscreen = False

def display_messages(msg):
    if "errors" in msg and msg["errors"]:
        st.error("\n".join(msg["errors"]))
    if "success" in msg and msg["success"]:
        st.success(msg["success"])
    elif "warning" in msg and msg["warning"]:
        st.warning(msg["warning"])  

def enable_notes_display():
    st.session_state.show_notes = not st.session_state.show_notes
    st.session_state.show_notes_msg = "Hide Notes" if st.session_state.show_notes else "Show Notes"    

def get_legal_json_filename(image_ref):
    ref = re.sub(r"[\/]", "#", image_ref)
    ref = re.sub(r"[:]", "$", ref)
    ref = re.sub(r"\.(jpg)|(jpeg)|(png)", "", ref, flags=re.IGNORECASE)
    filename = f"{TRANCRIPTION_FOLDER}/transcripts/{ref}-transcript.json" 
    return filename  

def get_timestamp():
    return  time.strftime("%Y-%m-%d-%H%M-%S")      

def new_chat():
    st.session_state.chat_history = ""
    st.session_state.chat_area = ""
    st.session_state.current_chat = f"{st.session_state.session_obj.user_name}: "
            
def open_fullscreen():
    """Callback to switch 'fullscreen' on."""
    st.session_state.fullscreen = True

def process_images_callback():
    "volume_name_input"
    volume_name = st.session_state.get("volume_name_input", "volume_name")
    st.session_state.session_obj.process_images(volume_name)
    msg = st.session_state.session_obj.msg
    display_messages(msg)
    st.session_state.pause_button_enabled = msg["pause_button_enabled"]
    st.session_state.status_msg = "\n".join(msg["status"])
    st.session_state.session_obj.reset_msg()
 
def reset_status_bar_message():
    st.session_state.status_msg = ""

def save_table_edits():
    edited_elements = st.session_state["my_key"]["edited_rows"]
    print(f"{edited_elements = }")
    st.session_state.session_obj.save_table_edits(edited_elements)
    
def show_fullscreen_image():
    st.write("## Full-Screen Image Viewer")
    image = st.session_state.session_obj.volume.current_image
    st.image(image, caption=f"Full Screen of Image {current_image_idx + 1}", use_container_width=True)
    st.button("Close Full Screen", on_click=close_fullscreen)

def update_table_content_option():
    st.session_state.session_obj.table_content_option = "content" if st.session_state.show_content_type=="transcript" else st.session_state.show_content_type
    #st.rerun()

def update_fieldvalue():
    fieldvalue = st.session_state.fieldvalue_key
    st.session_state.session_obj.update_fieldvalue(fieldvalue)

def update_table_type():
    st.session_state.session_obj.table_type = st.session_state.show_table_type
    #update_table_content_option()
    st.rerun()
            

def update_text_output():
    current_output_as_text = st.session_state.text_output_key
    st.session_state.session_obj.update_text_output(current_output_as_text)         

# State Management
def init_session_state():
    """Initialize session state variables"""
    if 'config' not in st.session_state:
        st.session_state.config = {}
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
        st.session_state.env_loaded = True
        return True
    return False

def main():
    st.set_page_config(page_title="Herbarium Parser (Callbacks, with Model & Prompt in Output)", layout="wide")
    init_session_state()
    if not st.session_state.env_loaded and load_env_to_session():
        st.success("Existing configuration loaded from .env file")
    
    st.markdown("""
        <style>
        /* Override dark mode */
        html[data-theme="light"] {
            color-scheme: light;
        }
        html[data-theme="dark"] {
            color-scheme: light !important;
        }
        html {
            color-scheme: light;
            data-theme: "light";
        }
        /* Rest of your styles */
        .stApp {
            background-color: beige !important;
        }
        div.stButton > button {
            background-color: #E0E0E0;
        }
        [data-testid="stHorizontalBlock"] {
            background-color: #FFFDD0 !important;
            padding: 1rem !important;
            border-radius: 5px !important;
        }
        div[data-testid="stContainer"] {
            padding: 0.5rem !important;
            margin: 0.5rem 0 !important;
        }
        .block-container {
            padding: 1rem !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.5rem !important;
            padding: 0.5rem !important;
        }
        /* Reduce spacing between elements */
    div.stTextArea {
        margin-bottom: 0.0rem !important;
    }
    
    div.row-widget.stButton {
        margin-top: 0.0rem !important;
        margin-bottom: 0.0rem !important;
    }
    
    /* Reduce padding between elements */
    div.element-container {
        padding-top: 0.0rem !important;
        padding-bottom: 0.0rem !important;
    }

        </style>
    
        <meta name="color-scheme" content="only light">
    """, unsafe_allow_html=True)
    

    set_up()
    user_name = st.text_input("username:", value="")
    if user_name == "":
        st.warning("Please enter your name.")
        st.stop()
    if "session_obj" not in st.session_state or st.session_state.session_obj is None:
        st.session_state.session_obj = Session(user_name)
    processing_type = st.radio("Select Processing Operation:", ["Process New Images", "Edit Saved Processed Images"])
    if processing_type == "Process New Images":
        # Input Settings
        input_settings_container = st.container(border=True)
        with input_settings_container:
            st.write("## Input Settings")
            if not os.path.isdir(PROMPT_FOLDER):
                st.warning(f"Prompt folder '{PROMPT_FOLDER}' does not exist.")
                prompt_files = []
            else:
                prompt_files = [f for f in os.listdir(PROMPT_FOLDER) if f.endswith(".txt")]
                prompt_files.sort()
            if prompt_files:
                selected_prompt_file = st.selectbox("Select a Prompt:", prompt_files)
                with open(os.path.join(PROMPT_FOLDER, selected_prompt_file), "r", encoding="utf-8") as pf:
                    st.session_state.session_obj.input_dict["prompt_text"] = pf.read().strip()
                    st.session_state.session_obj.input_dict["selected_prompt_filename"] = selected_prompt_file
            else:
                st.warning("No .txt prompt files found in the prompt folder.")
                selected_prompt_file = ""
            if st.session_state.session_obj.input_dict["prompt_text"]:
                llm_options = ["claude-3.5-sonnet", "gpt-4o"]
                selected_llms = st.multiselect("Select LLM(s):", llm_options, default=[llm_options[0]])
                api_key_dict = {f"{llm}_key": None for llm in selected_llms}
                if "OPENAI_API_KEY" in os.environ:
                    api_key_dict["gpt-4o_key"] = os.getenv("OPENAI_API_KEY")
                if "ANTHROPIC_API_KEY" in os.environ:
                    api_key_dict["claude-3.5-sonnet_key"] = os.getenv("ANTHROPIC_API_KEY")
                for llm in selected_llms:
                    if f"{llm}_key" in api_key_dict:
                        continue
                    api_key_file = st.file_uploader(f"Upload API Key File For {llm} (TXT)", type=["txt"])
                    if api_key_file:
                        api_key = api_key_file.read().decode("utf-8").strip()    
                        api_key_dict[llm] = api_key_file
                        api_key_dict[f"{llm}_key"] = api_key
                st.session_state.session_obj.input_dict["api_key_dict"] = api_key_dict
                st.session_state.session_obj.input_dict["selected_llms"] = selected_llms
                # Input type selection
                input_type = st.radio(
                    "Select Image Input Type:",
                    ["", "URL List", "Local Images"],
                    index=0,
                    label_visibility="visible"
                )
                if input_type == "URL List":
                    url_file = st.file_uploader("Upload URL List File", type=["txt"])
                    if url_file:
                        urls_content = url_file.read().decode("utf-8")
                        urls = urls_content.strip().splitlines()
                        st.write(f"Found {len(urls)} URLs in file")
                        st.session_state.session_obj.input_dict["selected_images_info"] = urls
                        st.session_state.session_obj.input_dict["images_info_type"] = "urls"
                elif input_type == "Local Images":
                    uploaded_files = st.file_uploader(
                        "Upload Image Files",
                        type=["png", "jpg", "jpeg"],
                        accept_multiple_files=True
                    )
                    if uploaded_files:
                        st.session_state.session_obj.input_dict["selected_images_info"] = uploaded_files
                        st.session_state.session_obj.input_dict["images_info_type"] = "local_images"
                        st.write("Selected files:")
                        for file in uploaded_files:
                            st.write(f"- {file.name}")
            # Clear selection button
            if st.session_state.session_obj.input_dict["selected_images_info"] and st.button("Clear Selection"):
                st.session_state.session_obj.input_dict["selected_images_info"] = []
                st.session_state.session_obj.input_dict["images_info_type"] = ""
                st.rerun()
# end input_setting_container
# Process Images Button
        process_container = st.container(border=True)
        if all(list(st.session_state.session_obj.input_dict.values())):
            process_container = st.container(border=True)
            if all(list(st.session_state.session_obj.input_dict.values())):
                with process_container:
                    st.container(height=20, border=False)
                    
                    # Initialize the volume name in session state if it doesn't exist
                    if 'volume_name' not in st.session_state:
                        st.session_state.volume_name = f"{st.session_state.session_obj.user_name}-{get_timestamp()}"
                    
                    st.write("Accept or Change this name for this run:")
                    # Use session state for the text input
                    st.session_state.volume_name = st.text_input(
                        "Enter a name for the volume and click Ctrl+Enter to accept", 
                        value=st.session_state.volume_name,
                        key="volume_name_input"
                    )
                    
                    st.button(
                        f"Process Images for {st.session_state.volume_name}",
                        on_click=process_images_callback
                    )
                    
                    status_bar_col, pause_button_col = st.columns([4, 2])
                    with status_bar_col:        
                        status_bar = st.text_area("Status:", st.session_state.status_msg, height=100)
            
                if st.session_state.pause_button_enabled:
                    with pause_button_col:
                        proceed_option = st.radio("How to Proceeed?:", ["Pause", "Retry Failed and Remaining Jobs", "Finish Remaining Jobs", "Cancel All Jobs", "Cancel All Jobs and Abort Editing"])
                        if proceed_option == "Finish Remaining Jobs":
                            st.session_state.status_msg = "Skipping Failed Jobs and Finishing remaining jobs..."
                            st.session_state.session_obj.resume_jobs(try_failed_jobs=False)
                        elif proceed_option == "Retry Failed and Remaining Jobs":
                            st.session_state.status_msg = "Retrying Failed Jobs and Finishing remaining jobs..."
                            st.session_state.session_obj.resume_jobs(try_failed_jobs=True)
                        elif proceed_option == "Cancel all Jobs and Abort Editing":
                            st.session_state.pause_button_enabled = False
                            st.session_state.status_msg = "Cancelling remaining jobs and aborting editing..."
                            st.wait(3)
                            st.session_state.session_obj.reset_inputs()
                            reset_states()
                        elif proceed_option == "Cancel All Jobs":
                            st.session_state.pause_button_enabled = False
                            st.session_state.status_msg = "Cancelling remaining jobs..."
                            st.wait(3)
                            st.session_state.session_obj.reset_inputs()
                elif st.session_state.session_obj.volume and st.session_state.session_obj.volume.pages:
                    st.session_state.session_obj.volume.commit_volume()              
        ##############################                         
    else:
        if not st.session_state.reedit_mode:
            st.session_state.reedit_mode = True
        load_saved_edits_container = st.container(border=True)     
        with load_saved_edits_container:
            volume_files = [f for f in os.listdir(f"{TRANCRIPTION_FOLDER}/volumes") if f.endswith(".json")]
            if volume_files:
                sorted_volume_files = st.session_state.session_obj.sort_filenames_by_timestamp(volume_files)
                selected_volume_file = st.radio("Select Volume File:", sorted_volume_files)
                col1, col2 = st.columns(2)
                with col1:
                    if selected_volume_file:
                        if st.button(f"Load: {selected_volume_file}"):
                            st.session_state.session_obj.re_edit_volume(selected_volume_file=selected_volume_file)
                            msg = st.session_state.session_obj.msg
                            display_messages(msg)
                            st.session_state.session_obj.reset_msg()
                with col2:
                    if st.button("Cancel"):
                        st.session_state.reedit_mode = False
                        st.rerun()    
            else:
                st.warning("No .json files found in the volumes folder.")
                if st.button("Cancel"):
                    st.session_state.reedit_mode = False
                    st.rerun()
        
            # end load_saved_edits_container
    # ---------------
    # Output Display
    #---------------
    if st.session_state.session_obj.pages:
        st.session_state.session_obj.volume.set_current_page()
        editor_container = st.container(border=False) 
        with editor_container:
            current_image_idx = st.session_state.session_obj.volume.current_page_idx
            col_image, col_editor = st.columns([4,3])
            with col_image:
                image = st.session_state.session_obj.volume.current_image
                st.image(image, caption=None, use_container_width=True)
            with col_editor:            
                col_text, col_fullscreen_button = st.columns([2,1])
                st.write(f"### Image {current_image_idx+1}")
                st.button("Open Full Screen", on_click=open_fullscreen)
                blank_space_height = 170 if st.session_state.get("editing_option", "Full Text")=="Full Text" else 310    
                blank_space = st.container(border=False, height=blank_space_height)
                st.write("### Editor")
                st.write("https://ipa.typeit.org/full/")
                st.write("https://translate.google.com/") 
                st.session_state.editing_view_option = st.radio("Select Editor View:",  ["Full Text", "Fieldname"], key="editing_option", index=0)
                if st.session_state.editing_view_option == "Fieldname":
                    #st.session_state.session_obj.load_current_transcript_obj()
                    col_prev_field, col_next_field, __ = st.columns(3)
                    with col_next_field:
                        st.button("next field", on_click=st.session_state.session_obj.go_to_next_field)         
                    with col_prev_field:       
                        st.button("prev field", on_click=st.session_state.session_obj.go_to_previous_field)
                    fieldname = st.session_state.session_obj.volume.get_current_fieldname()
                    fieldvalue = st.session_state.session_obj.volume.get_current_fieldvalue()       
                    emoji = st.session_state.session_obj.get_validation_rating_with_emoji(fieldname)
                    md_fieldname = f"{fieldname} {emoji}"
                    st.write(f"#### {md_fieldname}")
                    st.session_state.field_text_area = st.text_area("*Press Ctrl+Enter to accept edits*", fieldvalue, on_change=update_fieldvalue, key="fieldvalue_key", height=68)
                nav_prev, nav_next, image_ref_column = st.columns([1,1,2])
                with nav_prev:
                    st.button("Prev", on_click=st.session_state.session_obj.go_previous_image)
                with nav_next:
                    st.button("Next", on_click=st.session_state.session_obj.go_next_image)
                with image_ref_column:
                    image_ref = st.session_state.session_obj.volume.current_image_ref
                    st.write(f"#### {image_ref}")
                if st.session_state.editing_view_option == "Full Text":
                    text_container = st.container(border=False)
                    with text_container:
                        output_as_text = st.session_state.session_obj.get_output_as_text_with_rating()           
                        txt = st.text_area("**Press Ctrl-Enter to Accept Changes**", output_as_text, height=325, key="text_output_key", on_change=update_text_output)
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
                
    
                
        # end editor_container
        table_column, table_display_options = st.columns([5,1])
        with table_column:
            table_type = st.session_state.session_obj.table_type
            content_type = st.session_state.session_obj.table_content_option
            if table_type == "page" and content_type == "content":
                current_output_dict = st.session_state.session_obj.volume.current_output_dict
                fieldnames = [k for k in current_output_dict.keys()]
                validation_ratings = [st.session_state.session_obj.get_validation_rating_with_emoji(fieldname) for fieldname in fieldnames]
                data = {"fieldname": [], "rating": validation_ratings}
                for fieldname, d in current_output_dict.items():
                    data["fieldname"].append(fieldname)
                    for k, v in d.items():
                        if k in ["notes", "new notes"] and not st.session_state.show_notes:
                            continue
                        if k not in data:
                            data[k] = []
                        data[k].append(v)
                df = pd.DataFrame(data)
                column_config={
                    "value": st.column_config.TextColumn(
                        "value",
                        width="large",
                    ),
                    "rating": st.column_config.TextColumn(
                        "rating",
                        width="small",
                        disabled=True  # Make rating column non-editable
                    ),
                    "fieldname": st.column_config.TextColumn(
                        "fieldname",
                        width="medium",
                        disabled=True  # Make fieldname column non-editable
                    ),
                    "notes": st.column_config.TextColumn(
                        "notes",
                        width="medium",
                        disabled=True  # Make notes column non-editable
                    ),
                    "new notes": st.column_config.TextColumn(
                        "new notes",
                        width="medium"
                    )
                }    
                edited_df = st.data_editor(
                    df, 
                    use_container_width=True, 
                    column_config=column_config, 
                    hide_index=True, 
                    key="my_key", 
                    height=st.session_state.get('table_height', 225)
                )
                table_height = st.slider("table height", min_value=100, max_value=600, value=225, label_visibility="collapsed", key="table_height")
                st.session_state.edited_elements = st.session_state["my_key"]["edited_rows"]
            else:
                data = st.session_state.session_obj.get_data_for_table()
                df = pd.DataFrame(data)
                edited_df = st.data_editor(
                    df, 
                    use_container_width=True, 
                    hide_index=True,
                    disabled=True
                )    
        # end table_column
        with table_display_options:
            selected_table_type = st.radio(
                "Table Type:",
                ["page", "volume"],
                key="show_table_type",
                on_change=update_table_type
            )
            content_options = st.session_state.session_obj.get_table_content_options()
            selected_content = st.radio(
                "Table Option:", 
                content_options, 
                key="show_content_type",
                on_change=update_table_content_option  # Add this callback
            )
            if st.session_state.session_obj.table_type == "page" and st.session_state.session_obj.table_content_option == "content":
                st.button(st.session_state.show_notes_msg, on_click=enable_notes_display)
            
        bottom_buttons_container = st.container(border=False)
        with bottom_buttons_container:
            col_save_table_edits, col_save_text, col_download, col_save_to_json, col_chat_button = st.columns(5)
            with col_save_table_edits:
                if st.session_state.session_obj.table_content_option == "content" and "my_key" in st.session_state and st.session_state["my_key"]["edited_rows"]:
                    st.button(label="Save Table Changes", 
                    on_click=save_table_edits,
                    help="Save the table edits to the current transcript"
                    )
            with col_save_text:
                st.button(label="Update Text Output", 
                on_click=st.session_state.session_obj.save_edits_as_text,
                help="Reflect edits to text output"
                )
            with col_download:
                volume_filename = st.session_state.session_obj.get_volume_filename()
                st.download_button(
                    label="Download Session as TXT",
                    data=st.session_state.session_obj.final_output,
                    file_name=volume_filename,
                    mime="text/plain",
                    help="Save the combined output file to your local machine"
                )
            with col_save_to_json:
                st.button(label="Commit and Save Volume", 
                on_click=st.session_state.session_obj.save_edits_to_json,
                help="Finalizes edits and data and saves individual transcript JSONs and a volume JSON file"
                )
            with col_chat_button:
                msg = "Chat with LLM" if not st.session_state.show_chat_area else "Send Chat"
                st.button(label=msg, 
                on_click=chat_with_llm,
                help="Chat with claude-3.5-sonnet" if not st.session_state.show_chat_area else "Send the chat to the LLM"
                )
            col_output, col_chat_area = st.columns(2)
            with col_output:
                st.write("### Final Output (Combined)")
                st.text_area("Combined Output:", st.session_state.session_obj.final_output, label_visibility="collapsed", height=600)
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
    if st.session_state.fullscreen and st.session_state.session_obj.volume.current_transcript_obj:
        show_fullscreen_image()

if __name__ == "__main__":
    main()