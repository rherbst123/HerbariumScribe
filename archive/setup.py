import os
import platform
import sys
import venv
import subprocess
from pathlib import Path
import streamlit as st

def create_virtual_environment():
    venv_path = Path("venv")
    if not venv_path.exists():
        venv.create(venv_path, with_pip=True)
        # Get the pip path in the virtual environment
        if platform.system() == "Windows":
            pip_path = venv_path / "Scripts" / "pip.exe"
        else:
            pip_path = venv_path / "bin" / "pip"
        
        # Install requirements
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"])
        subprocess.run([str(pip_path), "install", "--upgrade", "streamlit"])

def get_package_manager():
    system = platform.system()
    if system == "Darwin":  # MacOS
        return "pip3"
    return "pip"

def convert_dict_to_string(config_dict):
    """
    Converts a dictionary of configuration values to environment file format.
    Example: {'API_KEY': 'xyz'} becomes 'API_KEY=xyz'
    """
    return '\n'.join([f'{key}={value}' for key, value in config_dict.items()])

def save_to_env(contents):
    """
    Saves the configuration string to a .env file.
    Creates the file if it doesn't exist, overwrites if it does.
    """
    try:
        with open('.env', 'w') as f:
            f.write(contents)
    except Exception as e:
        raise Exception(f"Failed to save configuration: {str(e)}")


def main():
    st.title("HerbariumScribe Setup")
    
    # Initialize session state if not already done
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'config' not in st.session_state:
        st.session_state.config = {}

    # Display system information
    system = platform.system()
    st.write(f"Detected Operating System: {system}")
    
    # Step 1: Create virtual environment
    if st.session_state.step == 1:
        st.header("Step 1: Create Virtual Environment")
        if st.button("Create Virtual Environment"):
            create_virtual_environment()
            st.success("Virtual environment created successfully!")
            st.session_state.step = 2
            st.rerun()

    # Step 2: OpenAI API Configuration
    elif st.session_state.step == 2:
        st.header("Step 2: OpenAI API Configuration")
        input_method = st.radio("Choose input method for OpenAI API Key:", 
                              ["Enter manually", "Load from file"])
        
        if input_method == "Enter manually":
            api_key = st.text_input("Enter your OpenAI API Key:", type="password")
        else:
            api_file = st.file_uploader("Upload file containing OpenAI API Key", type=['txt'])
            if api_file is not None:
                api_key = api_file.getvalue().decode().strip()
            else:
                api_key = None

        if st.button("Save API Key") and api_key:
            st.session_state.config['OPENAI_API_KEY'] = api_key
            st.success("API Key saved!")
            st.session_state.step = 3
            st.rerun()

    # Step 3: Anthropic Configuration
    elif st.session_state.step == 3:
        st.header("Step 3: Anthropic Configuration")
        input_method = st.radio("Choose input method for Anthropic API Key:", 
                              ["Enter manually", "Load from file"])
        
        if input_method == "Enter manually":
            anthropic_key = st.text_input("Enter your Anthropic API Key:", type="password")
        else:
            api_file = st.file_uploader("Upload file containing Anthropic API Key", type=['txt'])
            if api_file is not None:
                anthropic_key = api_file.getvalue().decode().strip()
            else:
                anthropic_key = None
        
        if st.button("Save Anthropic Configuration") and anthropic_key:
            st.session_state.config['ANTHROPIC_API_KEY'] = anthropic_key
            st.success("Anthropic configuration saved!")
            st.session_state.step = 4
            st.rerun()

    # Step 4: Final Configuration
    elif st.session_state.step == 4:
        st.header("Final Step: Save Configuration")
        
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
                
                st.success("""
                Setup complete! You can now:
                - Close this window
                - Start using HerbariumScribe
                - Return to this setup any time to modify your configuration
                """)
            except Exception as e:
                st.error(f"Error saving configuration: {str(e)}")

if __name__ == "__main__":
    main()
