# Herbarium Scribe


Welcome to HerbariumScribe, a project that enables user review and editing of Large Language Model (LLM) generated transcriptions of herbarium specimen labels.

Creators and Contributors:

- Riley Herbst

- Dan Stille

- Jeff Gwilliam

- Matt von Konrat


## Interface Overview

HerbariumScribe provides a user interface to take label transcription through the steps:

 1) Initial LLM generation of a transcript with automatic saving of that transcript as an original version. Transcripts are collected in a volume when saved.

 2) Subsequent user review and editing of the transcript, saving edited transcripts as the most recent version. Older versions are still available for inspection and analysis.

 3) Re-editing of transcripts from saved volumes, with fields which carry over unchanged from session to session marked with a cross-validation rating.

 4) Importing CSVs and converting them into volumes for viewing and editing. Images need to be in the `temp_images` folder.

 5) Multiple means of viewing and editing transcripts in order to more closely focus on individual fields or more quickly edit full transcripts. An editable output table enabled with notetaking is also provided beneath the transcript.

 6) Saving a user's edited transcripts, i.e., their session's work, to their local machine.

 Additonally, the interface provides:

 7) the option of displaying LLM token usage and costs, time spent creating and/or editing each individual version and the volume as a whole.

 8) the option of displaying the degree of alignment--field by field and overall--of the most recent version with all previous versions

 9) the chance to "chat" with an LLM to answer questions about an image or its transcription. Currently the chat is with Anthropic's claude-3.5-sonnet, so an Anthropic api key must be provided at some point.

 
## Quickstart

This repository will require python 3.10 or higher

The generation of new transcripts will require api keys from  [Anthropic](https://console.anthropic.com/settings/admin-keys) and/or [OpenAI](https://platform.openai.com/docs/overview)

First, clone the repository. In the your command line interface, type:

`git clone https://github.com/rherbst123/HerbariumScribe.git`

 Next, install the streamlit package. In your Command Line Interface, type:

 `pip install --upgrade streamlit`

 Even if you have streamlit already installed, upgrading to the most recent version is highly recommended. 
 
Run the installation wizard. In your Command Line Interface:

`streamlit run setup.py`

 The installation process is explained below.

Run the application Transcriber.py. In your Command Line Interface, type:

`streamlit run transcriber.py`

Runtime of application is overviewed below.

 ### Setup
 
This repository will require python 3.10 or higher

The generation of new transcripts will require api keys from  [Anthropic](https://console.anthropic.com/settings/admin-keys) and/or [OpenAI](https://platform.openai.com/docs/overview)

First, clone the repository. In the your command line interface, type:

`git clone https://github.com/rherbst123/HerbariumScribe.git`

 Next, install the streamlit package. In your Command Line Interface, type:

 `pip install --upgrade streamlit`

 Even if you have streamlit already installed, upgrading to the most recent version is highly recommended.

 An installation wizard has been provided to install all necessary packages and to create the local variables which will make the runtime startup process faster.

 It is HIGHLY RECOMMENDED to run the installation wizard. Beyond installing requirements, directories will be created and the user will be prompted to enter api keys that will be stored on their local machine and not accidentally shared.

 To run the installation wizard, type into you Command Line Interface:

 `streamlit run setup.py`

 The installation wizard must run with streamlit. The installation wizard will open up in a tab in your browser.

 Or you can run the CLI based script:

 `python setup_cli.py`

If you need to set things up manually, these are the steps you must take:

1) Install streamlit, and upgrade it

2) Install all packages in `requirements.txt`. If `pip install -r requirements.txt` doesn't work right away, try creating a virtual environment first, and then install those packages.

3) Create a `.env` file in the root directory, with:

      `OPENAI_API_KEY="your key"`

      `ANTHROPIC_API_KEY="your key"`

An API_KEY can be left as an empty string if you don't plan on using those models from that provider

4) Create these empty folders, if they don't already exist:

`temp_images`, `llm_processing/raw_response_data`, `output`

`output/raw_llm_responses`, `output/transcripts`, `output/versions`, `output/volumes`

### AWS Bedrock Integration

HerbariumScribe now supports AWS Bedrock models for image processing. This allows you to use models like Claude 3 Haiku, Claude 3.5 Sonnet, and Amazon Nova directly through your AWS account without needing separate API keys.

To set up and use AWS Bedrock models:

1. Run the Bedrock setup script:
   ```
   python setup_bedrock.py
   ```

2. When prompted, test the Bedrock models to determine which ones work with image processing.

3. When running the transcriber, Bedrock models that passed the image test will appear in the LLM selection dropdown.

For detailed instructions, see [BEDROCK_SETUP.md](BEDROCK_SETUP.md).

### Runtime

The application transcriber.py can be run by typing into your Command Line Interface:

`streamlit run transcriber.py`

The user interface will pop up as a tab in their browser, just as the installation wizard had.

The user can follow the prompts to create new transcripts or re-edit older transcripts.

Images can be transcribed as collections and can be uploaded locally from a user's computer or downloaded via urls provided by the user.

Once new transcripts are generated by an LLM, or, older transcripts have been selected and loaded, the editor will open with a view of an image and its transcript. 

Options are provided for how to view the transcript. Beneath the editing area there is a table, which can variously display the transcript in spreadheet form with the ability to add and review notes, its comparison to earlier versions or data related to costs and time.

Buttons at the bottom of the page allow the user to save their work locally to .json file (also saves a .csv) or to save a .txt file to their downloads folder.