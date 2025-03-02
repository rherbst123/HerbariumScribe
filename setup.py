import os
import streamlit as st
from tkinter import filedialog
import tkinter as tk

def save_to_env(contents):
    with open(".env", "w", encoding="utf-8") as f:
        f.write(contents)    

def convert_dict_to_string(d):
    return "\n".join([f"{key} = {val}" for key, val in d.items()])

def read_api_key_from_file(file):
    return file.getvalue().decode("utf-8").strip()

def select_folder():
    try:
        # Create and hide the tkinter root window
        root = tk.Tk()
        root.attributes('-topmost', True)  # Make sure it appears on top
        root.withdraw()  # Hide the main window
        
        # Open the folder selection dialog
        folder_path = filedialog.askdirectory(parent=root)
        
        # Clean up the tkinter instance
        root.destroy()
        
        return folder_path
    except Exception as e:
        st.error(f"Error selecting folder: {str(e)}")
        return None

import os
import streamlit as st
from tkinter import filedialog
import tkinter as tk

# ... (keep the helper functions the same) ...

def main():
    st.title("HerbariumScribe Setup")
    st.write("""
    Welcome to HerbariumScribe! This setup wizard will help you configure your environment.
    
    All settings are optional and can be modified later. Your configuration will be stored 
    locally in a `.env` file, which is not shared with anyone else.
    """)

    # Initialize session state
    if 'config' not in st.session_state:
        st.session_state.config = {}
    if 'images_dir' not in st.session_state:
        st.session_state.images_dir = ""
    if 'url_dir' not in st.session_state:
        st.session_state.url_dir = ""
    if 'step' not in st.session_state:
        st.session_state.step = 1

    # Progressive setup steps
    if st.session_state.step == 1:
        st.header("Step 1: Anthropic API Key")
        st.write("""
        The Anthropic API key is used for the 'Chat with LLM' feature. 
        You can skip this step, but you'll need to provide the key when you want to use the chat feature.
        """)

        anthropic_key_method = st.radio(
            "How would you like to provide the Anthropic API key?",
            ["Upload file", "Enter manually", "Skip for now"],
            key="anthropic_method",
            help="The API key will be stored locally in your .env file"
        )

        if anthropic_key_method == "Upload file":
            uploaded_file = st.file_uploader("Upload file containing Anthropic API key", key="anthropic_file")
            if uploaded_file:
                st.session_state.config["ANTHROPIC_API_KEY"] = read_api_key_from_file(uploaded_file)
        elif anthropic_key_method == "Enter manually":
            st.session_state.config["ANTHROPIC_API_KEY"] = st.text_input(
                "Enter Anthropic API key", 
                type="password",
                help="Your API key is stored locally and never shared"
            )
        else:
            st.session_state.config["ANTHROPIC_API_KEY"] = ""

        if st.button("Continue to Step 2"):
            st.session_state.step = 2
            st.rerun()

    elif st.session_state.step == 2:
        st.header("Step 2: OpenAI API Key")
        st.write("""
        The OpenAI API key is optional and can be added later if needed.
        """)

        openai_key_method = st.radio(
            "How would you like to provide the OpenAI API key?",
            ["Upload file", "Enter manually", "Skip for now"],
            key="openai_method"
        )

        if openai_key_method == "Upload file":
            uploaded_file = st.file_uploader("Upload file containing OpenAI API key", key="openai_file")
            if uploaded_file:
                st.session_state.config["OPENAI_API_KEY"] = read_api_key_from_file(uploaded_file)
        elif openai_key_method == "Enter manually":
            st.session_state.config["OPENAI_API_KEY"] = st.text_input("Enter OpenAI API key", type="password")
        else:
            st.session_state.config["OPENAI_API_KEY"] = ""

        if st.button("Continue to Step 3"):
            st.session_state.step = 3
            st.rerun()

    elif st.session_state.step == 3:
        st.header("Step 3: Directory Configuration")
        st.write("""
        Configure default directories to save time during runtime.
        
        - **Local Images Folder**: Required for re-editing previous transcripts
        - **URL Text Files Folder**: Optional, for storing URL references
        """)

        # Local Images Folder
        st.subheader("Local Images Folder")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text_input("Local Images Folder Path", st.session_state.images_dir, key="images_path", disabled=True)
        with col2:
            if st.button("Browse", key="browse_images"):
                folder_path = select_folder()
                if folder_path:
                    st.session_state.images_dir = folder_path
                    st.session_state.config["LOCAL_IMAGES_FOLDER"] = folder_path
                    st.rerun()

        st.write("---")

        # URL Text Files Folder
        st.subheader("URL Text Files Folder (Optional)")
        col3, col4 = st.columns([3, 1])
        with col3:
            st.text_input("URL Text Files Folder Path", st.session_state.url_dir, key="url_path", disabled=True)
        with col4:
            if st.button("Browse", key="browse_url"):
                folder_path = select_folder()
                if folder_path:
                    st.session_state.url_dir = folder_path
                    st.session_state.config["URL_TXT_FILES_FOLDER"] = folder_path
                    st.rerun()

        if st.button("Continue to Final Step"):
            st.session_state.step = 4
            st.rerun()

    elif st.session_state.step == 4:
        st.header("Final Step: Save Configuration")
        st.write("""
        Review your settings and save them to your local environment.
        You can always modify these settings later by running the setup again 
        or by directly editing the `.env` file.
        """)

        # Show current configuration
        st.subheader("Current Configuration")
        for key, value in st.session_state.config.items():
            if "API_KEY" in key:
                st.write(f"{key}: {'[Set]' if value else '[Not Set]'}")
            else:
                st.write(f"{key}: {value or '[Not Set]'}")

        if st.button("Save Configuration"):
            try:
                contents = convert_dict_to_string(st.session_state.config)
                save_to_env(contents)
                st.success("Configuration saved successfully!")
                
                # Install requirements
                with st.spinner("Installing requirements..."):
                    os.system("pip install -r requirements.txt")
                st.success("""
                Setup complete! You can now:
                - Close this window
                - Start using HerbariumScribe
                - Return to this setup any time to modify your configuration
                """)
            except Exception as e:
                st.error(f"Error saving configuration: {str(e)}")

    # Add navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.step > 1:
            if st.button("← Previous Step"):
                st.session_state.step -= 1
                st.rerun()
    with col2:
        if st.session_state.step < 4:
            if st.button("Skip to Final Step →"):
                st.session_state.step = 4
                st.rerun()

if __name__ == "__main__":
    main()
