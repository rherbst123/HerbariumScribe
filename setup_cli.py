import os
import platform
import venv
import subprocess
from pathlib import Path
import getpass

def create_virtual_environment():
    print("Creating virtual environment...")
    venv_path = Path("venv")
    if not venv_path.exists():
        venv.create(venv_path, with_pip=True)
        # Get the pip path in the virtual environment
        if platform.system() == "Windows":
            pip_path = venv_path / "Scripts" / "pip.exe"
        else:
            pip_path = venv_path / "bin" / "pip"
        
        print("Installing requirements...")
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"])
        subprocess.run([str(pip_path), "install", "--upgrade", "streamlit"])
        print("Virtual environment setup complete!")
    else:
        print("Virtual environment already exists!")

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)    

def create_directories():
    directories = [
        "temp_images",
        "llm_processing/raw_reponse_data",
        "output",
        "output/raw_llm_responses",
        "output/transcripts",
        "output/versions",
        "output/volumes"
    ]
    print("Creating necessary directories...")
    for directory in directories:
        ensure_directory_exists(directory)
    print("Directories created successfully!")

def setup_api_keys():
    config = {}
    
    print("\nOpenAI API Configuration")
    print("-----------------------")
    openai_key = getpass.getpass("Enter your OpenAI API Key: ")
    if openai_key:
        config['OPENAI_API_KEY'] = openai_key

    print("\nAnthropic API Configuration")
    print("-------------------------")
    anthropic_key = getpass.getpass("Enter your Anthropic API Key: ")
    if anthropic_key:
        config['ANTHROPIC_API_KEY'] = anthropic_key

    return config

def save_config(config):
    try:
        with open('.env', 'w') as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")
        print("\nConfiguration saved successfully!")
    except Exception as e:
        print(f"Error saving configuration: {str(e)}")

def main():
    print("HerbariumScribe Setup")
    print("=====================")
    print(f"Detected Operating System: {platform.system()}")

    while True:
        print("\nSetup Steps:")
        print("1. Create virtual environment and install dependencies")
        print("2. Create necessary directories")
        print("3. Configure API keys")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")

        if choice == "1":
            create_virtual_environment()
        elif choice == "2":
            create_directories()
        elif choice == "3":
            config = setup_api_keys()
            save_config(config)
        elif choice == "4":
            print("\nSetup complete! You can now start using HerbariumScribe.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
