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

def select_folder():
    system = platform.system()
    
    if system == "Windows":
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.attributes('-topmost', True)
            root.withdraw()
            folder_path = filedialog.askdirectory(parent=root)
            root.destroy()
            return folder_path
        except Exception as e:
            st.error(f"Error selecting folder: {str(e)}")
            return None
    else:
        # Alternative folder selection for Mac/Linux
        return st.text_input("Enter folder path:", 
                           help="Enter the full path to your folder")

def install_requirements():
    system = platform.system()
    pip_cmd = get_package_manager()
    
    if system == "Darwin":  # MacOS
        try:
            # Check if tkinter is available
            import tkinter
        except ImportError:
            st.error("""
            Tkinter is not installed. You can install it using one of these methods:
            1. Using Homebrew: `brew install python-tk`
            2. Using Python.org installer
            3. Continue without GUI folder selection
            """)
    
    try:
        with st.spinner("Installing requirements..."):
            subprocess.run([pip_cmd, "install", "-r", "requirements.txt"])
            subprocess.run([pip_cmd, "install", "--upgrade", "streamlit"])
        st.success("Requirements installed successfully!")
    except Exception as e:
        st.error(f"Error installing requirements: {str(e)}")

def main():
    st.title("HerbariumScribe Setup")
    
    # Display system information
    system = platform.system()
    st.write(f"Detected Operating System: {system}")
    
    # Create virtual environment first
    if st.button("Create Virtual Environment"):
        create_virtual_environment()
        st.success("Virtual environment created successfully!")

    # Rest of your existing setup.py code...
    
    # Modify the final step to use the new install_requirements function
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
                
                # Install requirements using the new function
                install_requirements()
                
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
