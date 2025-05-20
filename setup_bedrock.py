#!/usr/bin/env python3
"""
Setup script for AWS Bedrock integration with HerbariumScribe.
This script creates necessary folders, installs requirements, and configures AWS credentials.
"""

import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import subprocess
import platform
import shutil
import venv
from pathlib import Path
import json
import boto3
import time

# Define colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Application directories
DIRECTORIES = [
    "temp_images",
    "output/raw_llm_responses",
    "output/transcripts",
    "output/versions",
    "output/volumes",
    "prompts",
    "logs",
    "llm_processing/bedrock/model_info"
]

# Requirements for Bedrock
REQUIREMENTS = [
    "boto3",
    "botocore",
    "python-dotenv",
    "pillow",
    "streamlit"
]

# Virtual environment name
VENV_NAME = "venv"

def print_header(message):
    """Print a formatted header message"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {message} ==={Colors.ENDC}\n")

def print_success(message):
    """Print a success message"""
    print(f"{Colors.GREEN}+ {message}{Colors.ENDC}")

def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.WARNING}! {message}{Colors.ENDC}")

def print_error(message):
    """Print an error message"""
    print(f"{Colors.FAIL}x {message}{Colors.ENDC}")

def create_directories():
    """Create all necessary directories for the application"""
    print_header("Creating Application Directories")
    
    for directory in DIRECTORIES:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print_success(f"Created directory: {directory}")
            else:
                print_warning(f"Directory already exists: {directory}")
        except Exception as e:
            print_error(f"Failed to create directory {directory}: {str(e)}")

def check_gitignore():
    """Check if .gitignore file exists"""
    print_header("Checking .gitignore")
    
    if os.path.exists(".gitignore"):
        print_success(".gitignore file already exists")
    else:
        print_warning("No .gitignore file found")
        print_warning("Please create a .gitignore file manually or use a git client to generate one")
        print_warning("You should exclude: temp_images/, output/, logs/, venv/, .env")

def create_env_template():
    """Create a template .env file for AWS credentials"""
    print_header("Creating .env template")
    
    env_content = """# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# OpenAI API Key (optional)
OPENAI_API_KEY=your_openai_key_here

# Anthropic API Key (optional)
ANTHROPIC_API_KEY=your_anthropic_key_here

# Application Settings
DEBUG=False
"""
    
    try:
        if not os.path.exists(".env"):
            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_content)
            print_success("Created .env template file")
        else:
            print_warning(".env file already exists, skipping")
    except Exception as e:
        print_error(f"Failed to create .env template: {str(e)}")

def check_python_version():
    """Check if Python version is compatible"""
    print_header("Checking Python Version")
    
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 9):
        print_error(f"Python 3.9+ is required. You are using Python {major}.{minor}")
        print_warning("This code uses features that require Python 3.9+")
        return False
    
    print_success(f"Python version {major}.{minor} is compatible")
    return True

def create_virtual_environment():
    """Create a virtual environment"""
    print_header("Creating Virtual Environment")
    
    if os.path.exists(VENV_NAME):
        print_warning(f"Virtual environment '{VENV_NAME}' already exists")
        recreate = input(f"{Colors.BLUE}Do you want to recreate it? (y/n): {Colors.ENDC}")
        if recreate.lower() == 'y':
            try:
                shutil.rmtree(VENV_NAME)
                print_success(f"Removed existing virtual environment: {VENV_NAME}")
            except Exception as e:
                print_error(f"Failed to remove existing virtual environment: {str(e)}")
                return False
        else:
            return True
    
    try:
        venv.create(VENV_NAME, with_pip=True)
        print_success(f"Created virtual environment: {VENV_NAME}")
        return True
    except Exception as e:
        print_error(f"Failed to create virtual environment: {str(e)}")
        return False

def get_venv_python_path():
    """Get the path to the Python executable in the virtual environment"""
    if platform.system() == "Windows":
        return os.path.join(VENV_NAME, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_NAME, "bin", "python")

def get_venv_pip_path():
    """Get the path to the pip executable in the virtual environment"""
    if platform.system() == "Windows":
        return os.path.join(VENV_NAME, "Scripts", "pip.exe")
    else:
        return os.path.join(VENV_NAME, "bin", "pip")

def install_requirements_in_venv():
    """Install required Python packages in the virtual environment"""
    print_header("Installing Requirements in Virtual Environment")
    
    pip_path = get_venv_pip_path()
    
    # Upgrade pip first
    try:
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        print_success("Upgraded pip to the latest version")
    except Exception as e:
        print_warning(f"Failed to upgrade pip: {str(e)}")
    
    # Install each requirement
    for package in REQUIREMENTS:
        try:
            print(f"Installing {package}...")
            subprocess.run([pip_path, "install", package], check=True)
            print_success(f"Installed {package}")
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to install {package}: {str(e)}")
        except Exception as e:
            print_error(f"Error during installation of {package}: {str(e)}")
    
    # Create requirements.txt file
    try:
        subprocess.run([pip_path, "freeze"], stdout=open("requirements.txt", "w"), check=True)
        print_success("Created requirements.txt file")
    except Exception as e:
        print_error(f"Failed to create requirements.txt: {str(e)}")

def create_activation_scripts():
    """Create activation scripts for the virtual environment"""
    print_header("Creating Activation Scripts")
    
    # Create Windows activation script
    if platform.system() == "Windows":
        with open("activate.bat", "w") as f:
            f.write(f"@echo off\n"
                   f"echo Activating virtual environment...\n"
                   f"call {VENV_NAME}\\Scripts\\activate.bat\n"
                   f"echo Virtual environment activated. Type 'deactivate' to exit.\n")
        print_success("Created activate.bat for Windows")
    
    # Create Unix activation script
    else:
        with open("activate.sh", "w") as f:
            f.write(f"#!/bin/bash\n"
                   f"echo Activating virtual environment...\n"
                   f"source {VENV_NAME}/bin/activate\n"
                   f"echo Virtual environment activated. Type 'deactivate' to exit.\n")
        os.chmod("activate.sh", 0o755)  # Make executable
        print_success("Created activate.sh for Unix/Linux/Mac")

def configure_aws_credentials():
    """Configure AWS credentials for Bedrock access"""
    print_header("Configuring AWS Credentials")
    
    # Check if AWS credentials are already configured
    aws_creds_file = os.path.expanduser("~/.aws/credentials")
    aws_config_file = os.path.expanduser("~/.aws/config")
    
    if os.path.exists(aws_creds_file) and os.path.exists(aws_config_file):
        print_warning("AWS credentials files already exist")
        print_success("Using existing AWS configuration")
        return True
    
    # Get AWS credentials from user
    print("Please enter your AWS credentials:")
    aws_access_key = input(f"{Colors.BLUE}AWS Access Key ID: {Colors.ENDC}")
    aws_secret_key = input(f"{Colors.BLUE}AWS Secret Access Key: {Colors.ENDC}")
    aws_region = input(f"{Colors.BLUE}AWS Region (default: us-east-1): {Colors.ENDC}") or "us-east-1"
    
    # Create AWS credentials directory if it doesn't exist
    aws_dir = os.path.expanduser("~/.aws")
    if not os.path.exists(aws_dir):
        os.makedirs(aws_dir)
    
    # Write credentials file
    try:
        with open(aws_creds_file, "w") as f:
            f.write("[default]\n")
            f.write(f"aws_access_key_id = {aws_access_key}\n")
            f.write(f"aws_secret_access_key = {aws_secret_key}\n")
        
        # Write config file
        with open(aws_config_file, "w") as f:
            f.write("[default]\n")
            f.write(f"region = {aws_region}\n")
            f.write("output = json\n")
        
        print_success("AWS credentials configured successfully")
        
        # Update .env file with AWS credentials
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                env_content = f.read()
            
            # Replace AWS credentials in .env file
            env_content = env_content.replace("AWS_ACCESS_KEY_ID=your_access_key_here", f"AWS_ACCESS_KEY_ID={aws_access_key}")
            env_content = env_content.replace("AWS_SECRET_ACCESS_KEY=your_secret_key_here", f"AWS_SECRET_ACCESS_KEY={aws_secret_key}")
            env_content = env_content.replace("AWS_REGION=us-east-1", f"AWS_REGION={aws_region}")
            
            with open(".env", "w") as f:
                f.write(env_content)
            
            print_success("Updated .env file with AWS credentials")
        
        return True
    except Exception as e:
        print_error(f"Failed to configure AWS credentials: {str(e)}")
        return False

def test_bedrock_connection():
    """Test connection to AWS Bedrock"""
    print_header("Testing AWS Bedrock Connection")
    
    try:
        # Create Bedrock client
        bedrock_client = boto3.client('bedrock-runtime')
        
        # List available models
        bedrock_model_client = boto3.client('bedrock')
        response = bedrock_model_client.list_foundation_models()
        
        if 'modelSummaries' in response:
            models = response['modelSummaries']
            print_success(f"Successfully connected to AWS Bedrock")
            print_success(f"Found {len(models)} available models")
            
            # Save model information to file
            model_info_dir = "llm_processing/bedrock/model_info"
            if not os.path.exists(model_info_dir):
                os.makedirs(model_info_dir)
            
            with open(f"{model_info_dir}/model_info.json", "w") as f:
                json.dump(response, f, indent=2)
            
            print_success(f"Saved model information to {model_info_dir}/model_info.json")
            
            # Filter for vision models
            vision_models = [model for model in models if 'IMAGE' in model.get('inputModalities', [])]
            
            if vision_models:
                print_success(f"Found {len(vision_models)} vision-capable models:")
                for model in vision_models:
                    print(f"  - {model['modelId']}")
                
                # Save vision model information to file
                with open(f"{model_info_dir}/vision_model_info.json", "w") as f:
                    json.dump(vision_models, f, indent=2)
                
                print_success(f"Saved vision model information to {model_info_dir}/vision_model_info.json")
            else:
                print_warning("No vision-capable models found")
            
            return True
        else:
            print_error("Failed to retrieve model list from AWS Bedrock")
            return False
    except Exception as e:
        print_error(f"Failed to connect to AWS Bedrock: {str(e)}")
        print_warning("Please check your AWS credentials and ensure you have access to the Bedrock service")
        return False

def run_model_tester():
    """Run the model_tester.py script to test vision models"""
    print_header("Testing Vision Models")
    try:
        # Check if model_tester.py exists
        model_tester_path = "llm_processing/bedrock/model_tester.py"
        if not os.path.exists(model_tester_path):
            print_error(f"Model tester script not found at {model_tester_path}")
            return False
        
        # Create test_images directory if it doesn't exist
        test_images_dir = "test_images"
        if not os.path.exists(test_images_dir):
            os.makedirs(test_images_dir)
            print_success(f"Created directory: {test_images_dir}")
        
        # Check if there's a test image
        test_image_found = False
        for file in os.listdir(test_images_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                test_image_found = True
                break
        
        if not test_image_found:
            print_warning("No test images found in test_images directory")
            print_warning("Please add at least one image to the test_images directory")
            return False
        
        # Run the model tester script
        print("Running model tester script...")
        
        # Determine which Python to use
        if os.path.exists(VENV_NAME):
            python_path = get_venv_python_path()
        else:
            python_path = sys.executable
        
        # Run the model tester
        try:
            # Change to the bedrock directory to run the script
            #current_dir = os.getcwd()
            #os.chdir("llm_processing/bedrock")
            
            # Run the script with the Python interpreter
            #subprocess.run([python_path, "llm_processing/bedrock/model_tester.py"], check=True)
            os.system("python llm_processing/bedrock/model_tester.py")
            # Change back to the original directory
            #os.chdir(current_dir)
            
            print_success("Model testing completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Model testing failed: {str(e)}")
            return False
    except Exception as e:
        print_error(f"Error running model tester: {str(e)}")
        return False

def main():
    """Main setup function"""
    print_header("HerbariumScribe AWS Bedrock Setup")
    
    if not check_python_version():
        print_warning("Continuing with setup, but some features may not work correctly.")
        proceed = input(f"{Colors.BLUE}Do you want to proceed anyway? (y/n): {Colors.ENDC}")
        if proceed.lower() != 'y':
            print_error("Setup aborted. Please install Python 3.9 or newer.")
            sys.exit(1)
    
    create_directories()
    check_gitignore()
    create_env_template()
    
    # Ask user if they want to create a virtual environment
    create_venv = input(f"{Colors.BLUE}Do you want to create a virtual environment? (y/n): {Colors.ENDC}")
    if create_venv.lower() == 'y':
        if create_virtual_environment():
            install_requirements_in_venv()
            create_activation_scripts()
    else:
        # Ask user if they want to install requirements globally
        install_req = input(f"{Colors.BLUE}Do you want to install Python requirements globally? (y/n): {Colors.ENDC}")
        if install_req.lower() == 'y':
            # Determine pip command based on platform
            pip_cmd = "pip"
            if platform.system() != "Windows":
                try:
                    subprocess.run(["pip3", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    pip_cmd = "pip3"
                except:
                    pip_cmd = "pip"
            
            # Install each requirement
            for package in REQUIREMENTS:
                try:
                    print(f"Installing {package}...")
                    subprocess.run([pip_cmd, "install", package], check=True)
                    print_success(f"Installed {package}")
                except Exception as e:
                    print_error(f"Error during installation of {package}: {str(e)}")
    
    # Configure AWS credentials
    configure_aws = input(f"{Colors.BLUE}Do you want to configure AWS credentials now? (y/n): {Colors.ENDC}")
    if configure_aws.lower() == 'y':
        configure_aws_credentials()
    
    # Test Bedrock connection
    test_bedrock = input(f"{Colors.BLUE}Do you want to test the connection to AWS Bedrock? (y/n): {Colors.ENDC}")
    if test_bedrock.lower() == 'y':
        test_bedrock_connection()
        
    # Run model tester
    test_models = input(f"{Colors.BLUE}Do you want to run the model tester to test vision models? (y/n): {Colors.ENDC}")
    if test_models.lower() == 'y':
        run_model_tester()
    
    print_header("Setup Complete!")
    
    if create_venv.lower() == 'y':
        if platform.system() == "Windows":
            activate_cmd = "activate.bat"
        else:
            activate_cmd = "source activate.sh"
        
        print(f"""
{Colors.GREEN}Your HerbariumScribe AWS Bedrock integration is ready to use!{Colors.ENDC}

To activate the virtual environment:
- Windows: Run {Colors.BOLD}activate.bat{Colors.ENDC}
- Unix/Linux/Mac: Run {Colors.BOLD}source activate.sh{Colors.ENDC}

After activating the virtual environment:
1. Make sure your AWS credentials are properly configured
2. Run the app with: {Colors.BOLD}python transcriber.py{Colors.ENDC}

{Colors.BLUE}Happy transcribing with AWS Bedrock!{Colors.ENDC}
""")
    else:
        print(f"""
{Colors.GREEN}Your HerbariumScribe AWS Bedrock integration is ready to use!{Colors.ENDC}

To run the application:
1. Make sure your AWS credentials are properly configured
2. Run the app with: {Colors.BOLD}python transcriber.py{Colors.ENDC}

{Colors.BLUE}Happy transcribing with AWS Bedrock!{Colors.ENDC}
""")

if __name__ == "__main__":
    main()