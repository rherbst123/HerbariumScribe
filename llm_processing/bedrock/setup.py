#!/usr/bin/env python3
"""
Setup script for Field Museum Bedrock Transcription application.
This script creates necessary folders, installs requirements, and sets up .gitignore.
"""

import os
import sys
import subprocess
import platform
import shutil
import venv
from pathlib import Path

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
    "transcriptions",
    "raw_llm_responses",
    "prompts",
    "logs",
    "data",
    "test_images",
    "test_results",
    "model_info"  # Added model_info directory
]

# Requirements for the application
REQUIREMENTS = [
    "streamlit",
    "boto3",
    "requests",
    "python-dotenv",
    "pillow",
    "tabulate",
    "pandas"
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
    
    # Create a sample prompt file if prompts directory is empty
    prompts_dir = Path("prompts")
    if not any(prompts_dir.iterdir()) if prompts_dir.exists() else False:
        sample_prompt_path = prompts_dir / "sample_prompt.txt"
        with open(sample_prompt_path, "w", encoding="utf-8") as f:
            f.write("Please transcribe all text visible in this image. Include any handwritten notes, typed text, labels, and captions.\n\n"
                    "Format your response as plain text, preserving the layout as much as possible.\n\n"
                    "If there are any parts that are illegible or uncertain, indicate this with [illegible].")
        print_success("Created sample prompt file")
    
    # Create a sample test image if test_images directory is empty
    test_images_dir = Path("test_images")
    if not any(test_images_dir.iterdir()) if test_images_dir.exists() else False:
        # Create a .gitkeep file to ensure the directory is tracked by git
        gitkeep_path = test_images_dir / ".gitkeep"
        with open(gitkeep_path, "w") as f:
            pass
        print_success("Created .gitkeep file in test_images directory")
        print_warning("Please add test images to the test_images directory")

def check_gitignore():
    """Check if .gitignore file exists"""
    print_header("Checking .gitignore")
    
    if os.path.exists(".gitignore"):
        print_success(".gitignore file already exists")
    else:
        print_warning("No .gitignore file found")
        print_warning("Please create a .gitignore file manually or use a git client to generate one")
        print_warning("You should exclude: temp_images/, transcriptions/, raw_llm_responses/, logs/, data/, venv/, .env")

def create_env_template():
    """Create a template .env file"""
    print_header("Creating .env template")
    
    env_content = """# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

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
        print_warning("This code uses features like dictionary merging with the '|' operator that require Python 3.9+")
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

def generate_model_info():
    """Generate model information files"""
    print_header("Generating Model Information")
    
    try:
        # Import here to avoid issues if it's not available
        from model_manager import ModelManager
        
        manager = ModelManager()
        
        # Generate model_info.json
        manager.save_model_info()
        
        # Generate vision_model_info.json
        manager.save_vision_model_info()
        
        print_success("Generated model information files")
        return True
    except ImportError:
        print_warning("Could not import ModelManager. Make sure to run this after installing requirements.")
        print_warning("You can generate model information later by running: python model_manager.py")
        return False
    except Exception as e:
        print_error(f"Error generating model information: {str(e)}")
        print_warning("You can generate model information later by running: python model_manager.py")
        return False

def test_vision_models(limited_test=False):
    """Test vision models for image processing capabilities"""
    print_header("Testing Vision Models")
    
    try:
        # Import here to avoid issues if it's not available
        from model_tester import ModelTester
        
        tester = ModelTester()
        
        # Load models from vision_model_info.json
        models = tester.load_models()
        
        if not models:
            print_warning("No vision models found. Make sure to run model_manager.py first.")
            return False
        
        print(f"Found {len(models)} vision models.")
        
        if limited_test:
            # Test only Claude models for quick setup
            claude_models = [m for m in models if "claude" in m.get("modelId", "").lower()]
            if claude_models:
                print(f"Testing {len(claude_models)} Claude models for quick setup...")
                results = tester.test_models(claude_models)
            else:
                print_warning("No Claude models found. Testing first model only...")
                results = tester.test_models([models[0]])
        else:
            # Test all models
            print("Testing all vision models. This may take a while...")
            results = tester.test_models(models)
        
        # Update vision_model_info.json with test results
        tester.update_model_info(results)
        
        # Print summary
        tester.print_summary(results)
        
        print_success("Vision model testing completed")
        return True
    except ImportError:
        print_warning("Could not import ModelTester. Make sure to run this after installing requirements.")
        print_warning("You can test vision models later by running: python model_tester.py")
        return False
    except Exception as e:
        print_error(f"Error testing vision models: {str(e)}")
        print_warning("You can test vision models later by running: python model_tester.py")
        return False

def main():
    """Main setup function"""
    print_header("Field Museum Bedrock Transcription App Setup")
    
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
            
            # Ask if user wants to generate model information
            generate_info = input(f"{Colors.BLUE}Do you want to generate model information now? (y/n): {Colors.ENDC}")
            if generate_info.lower() == 'y':
                # Activate the virtual environment and run the model manager
                python_path = get_venv_python_path()
                try:
                    subprocess.run([python_path, "-m", "model_manager"], check=True)
                    print_success("Generated model information")
                    
                    # Ask if user wants to test vision models
                    test_models = input(f"{Colors.BLUE}Do you want to test vision models now? This may take some time. (y/n/quick): {Colors.ENDC}")
                    if test_models.lower() == 'y':
                        # Test all vision models
                        subprocess.run([python_path, "-m", "model_tester"], check=True)
                        print_success("Tested vision models")
                    elif test_models.lower() == 'quick':
                        # Test only Claude models for quick setup
                        subprocess.run([python_path, "-c", "from model_tester import ModelTester; tester = ModelTester(); models = [m for m in tester.load_models() if 'claude' in m.get('modelId', '').lower()]; results = tester.test_models(models); tester.update_model_info(results); tester.print_summary(results)"], check=True)
                        print_success("Tested Claude vision models")
                except Exception as e:
                    print_error(f"Error generating model information: {str(e)}")
                    print_warning("You can generate model information later by running: python model_manager.py")
                    print_warning("You can test vision models later by running: python model_tester.py")
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
            
            # Ask if user wants to generate model information
            generate_info = input(f"{Colors.BLUE}Do you want to generate model information now? (y/n): {Colors.ENDC}")
            if generate_info.lower() == 'y':
                try:
                    subprocess.run([sys.executable, "-m", "model_manager"], check=True)
                    print_success("Generated model information")
                    
                    # Ask if user wants to test vision models
                    test_models = input(f"{Colors.BLUE}Do you want to test vision models now? This may take some time. (y/n/quick): {Colors.ENDC}")
                    if test_models.lower() == 'y':
                        # Test all vision models
                        subprocess.run([sys.executable, "-m", "model_tester"], check=True)
                        print_success("Tested vision models")
                    elif test_models.lower() == 'quick':
                        # Test only Claude models for quick setup
                        subprocess.run([sys.executable, "-c", "from model_tester import ModelTester; tester = ModelTester(); models = [m for m in tester.load_models() if 'claude' in m.get('modelId', '').lower()]; results = tester.test_models(models); tester.update_model_info(results); tester.print_summary(results)"], check=True)
                        print_success("Tested Claude vision models")
                except Exception as e:
                    print_error(f"Error generating model information: {str(e)}")
                    print_warning("You can generate model information later by running: python model_manager.py")
                    print_warning("You can test vision models later by running: python model_tester.py")
    
    print_header("Setup Complete!")
    
    if create_venv.lower() == 'y':
        if platform.system() == "Windows":
            activate_cmd = "activate.bat"
        else:
            activate_cmd = "source activate.sh"
        
        print(f"""
{Colors.GREEN}Your Field Museum Bedrock Transcription App is ready to use!{Colors.ENDC}

To activate the virtual environment:
- Windows: Run {Colors.BOLD}activate.bat{Colors.ENDC}
- Unix/Linux/Mac: Run {Colors.BOLD}source activate.sh{Colors.ENDC}

After activating the virtual environment:
1. Make sure to update your AWS credentials in the .env file
2. Run the app with: {Colors.BOLD}streamlit run app.py{Colors.ENDC}
3. Generate model information: {Colors.BOLD}python model_manager.py{Colors.ENDC}
4. Test vision models: {Colors.BOLD}python model_tester.py{Colors.ENDC}

{Colors.BLUE}Happy transcribing!{Colors.ENDC}
""")
    else:
        print(f"""
{Colors.GREEN}Your Field Museum Bedrock Transcription App is ready to use!{Colors.ENDC}

To run the application:
1. Make sure to update your AWS credentials in the .env file
2. Run the app with: {Colors.BOLD}streamlit run app.py{Colors.ENDC}
3. Generate model information: {Colors.BOLD}python model_manager.py{Colors.ENDC}
4. Test vision models: {Colors.BOLD}python model_tester.py{Colors.ENDC}

{Colors.BLUE}Happy transcribing!{Colors.ENDC}
""")

if __name__ == "__main__":
    main()