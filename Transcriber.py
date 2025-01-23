import streamlit as st
import os
import queue
from datetime import datetime
from PIL import Image
from io import BytesIO

# Import your processors
from processors.claude_url import ClaudeImageProcessorThread
from processors.gpt_url import GPTImageProcessorThread
from processors.claude_local import ClaudeLocalImageProcessorThread
from processors.gpt_local import GPTLocalImageProcessorThread


PROMPT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def main():
    st.set_page_config(page_title="Field Museum Herbarium Parser", layout="wide")

    # Session state variables
    if "processed_images" not in st.session_state:
        st.session_state.processed_images = []
    if "processed_outputs" not in st.session_state:
        st.session_state.processed_outputs = []
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
    # NEW: Track whether user wants a "full-screen" zoom of current image
    if "fullscreen" not in st.session_state:
        st.session_state.fullscreen = False

    # ---------------
    # Prompt Selection
    # ---------------
    st.write("## Prompt Selection")

    if not os.path.isdir(PROMPT_FOLDER):
        st.warning(f"Prompt folder '{PROMPT_FOLDER}' does not exist or is not accessible.")
        prompt_files = []
    else:
        prompt_files = [f for f in os.listdir(PROMPT_FOLDER) if f.endswith(".txt")]
        prompt_files.sort()

    if prompt_files:
        selected_prompt_file = st.selectbox("Select a Prompt:", prompt_files)
        # Read the selected prompt file
        with open(os.path.join(PROMPT_FOLDER, selected_prompt_file), "r", encoding="utf-8") as pf:
            prompt_text_from_file = pf.read().strip()
    else:
        st.warning("No .txt files found in the prompt folder.")
        prompt_text_from_file = ""

    # ---------------
    # Input Settings
    # ---------------
    st.write("## Input Settings")

  

    # Select LLM
    llm_options = ["Claude 3.5 Sonnet", "GPT-4o"]
    selected_llm = st.selectbox("Select LLM:", llm_options, index=0)

    # File uploader for API key
    api_key_file = st.file_uploader("Upload API Key File (TXT)", type=["txt"])
  
  
  # Radio for "Local Images" vs "URL List"
    input_type = st.radio(
        "Select Image Input Type:",
        ["URL List", "Local Images"],
        index=0
    )



    # URL file or local images
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
    # Process Images
    # ---------------
    if st.button("Process Images"):
        if not api_key_file:
            st.error("Please upload the API key file.")
        elif not prompt_text_from_file:
            st.error("No prompt text is available (folder empty or file missing).")
        else:
            # Read the API key
            try:
                api_key = api_key_file.read().decode("utf-8").strip()
            except:
                st.error("Unable to read API key file. Check encoding or file format.")
                st.stop()

            # Reset session states
            st.session_state.prompt_text = prompt_text_from_file
            st.session_state.processed_images = []
            st.session_state.processed_outputs = []
            st.session_state.current_image_index = 0
            st.session_state.final_output = ""
            st.session_state.urls = []
            st.session_state.local_images = []
            st.session_state.fullscreen = False  # Reset fullscreen

            # Create queue
            result_queue = queue.Queue()

            # URL-based or local
            if input_type == "URL List":
                if not url_file:
                    st.error("Please upload a .txt file containing image URLs.")
                    st.stop()

                try:
                    urls_content = url_file.read().decode("utf-8")
                    urls = urls_content.strip().splitlines()
                except:
                    st.error("Unable to read URL file. Check encoding or file format.")
                    st.stop()

                st.session_state.urls = urls

                # Decide which processor
                if selected_llm == "Claude 3.5 Sonnet":
                    processor_thread = ClaudeImageProcessorThread(api_key, st.session_state.prompt_text, urls, result_queue)
                else:
                    processor_thread = GPTImageProcessorThread(api_key, st.session_state.prompt_text, urls, result_queue)

                processor_thread.process_images()

            else:
                # Local images
                if not local_image_files:
                    st.error("Please upload at least one image file.")
                    st.stop()

                local_images_list = []
                for uploaded_file in local_image_files:
                    try:
                        image = Image.open(uploaded_file)
                        local_images_list.append((image, uploaded_file.name))
                    except Exception as e:
                        st.warning(f"Could not open {uploaded_file.name}: {e}")

                st.session_state.local_images = local_images_list

                # Decide which processor
                if selected_llm == "Claude 3.5 Sonnet":
                    processor_thread = ClaudeLocalImageProcessorThread(api_key, st.session_state.prompt_text, local_images_list, result_queue)
                else:
                    processor_thread = GPTLocalImageProcessorThread(api_key, st.session_state.prompt_text, local_images_list, result_queue)

                processor_thread.process_images()

            # Retrieve results
            while True:
                try:
                    image, output = result_queue.get_nowait()
                except queue.Empty:
                    break
                if image is None and output is None:
                    break
                if image:
                    st.session_state.processed_images.append(image)
                st.session_state.processed_outputs.append(output)
                st.session_state.final_output += output + "\n" + ("=" * 50) + "\n"

            if st.session_state.processed_images:
                st.success("Images processed successfully!")
            else:
                st.warning("No images or errors occurred. Check logs or outputs.")

    # ---------------
    # Output Display
    #---------------
    col1, col2 = st.columns([1, 2])

    with col1:
        st.write("### Image Preview")

        if st.session_state.processed_images:
            idx = st.session_state.current_image_index
            image = st.session_state.processed_images[idx]
            # The main image preview
            st.image(image, caption=f"Image {idx + 1}", use_container_width=True)

            # Button to open full screen
            if st.button("Open Full Screen"):
                st.session_state.fullscreen = True
                st.experimental_rerun()
        else:
            st.write("No processed images to display.")

        # Navigation
        nav_prev, nav_next = st.columns(2)
        with nav_prev:
            if st.button("Previous"):
                if st.session_state.current_image_index > 0:
                    save_current_output_in_session()
                    st.session_state.current_image_index -= 1
                    #st.experimental_rerun()

        with nav_next:
            if st.button("Next"):
                if st.session_state.current_image_index < len(st.session_state.processed_images) - 1:
                    save_current_output_in_session()
                    st.session_state.current_image_index += 1
                    #st.experimental_rerun()

    with col2:
        st.write("### Extracted/Parsed Text")
        if st.session_state.processed_outputs and st.session_state.processed_images:
            current_output = st.session_state.processed_outputs[st.session_state.current_image_index]
        else:
            current_output = ""

        # Editable text area
        edited_text = st.text_area(
            "Output Text:",
            current_output,
            height=300,
            key="output_text_area"
        )

    # ---------------
    # Full-Screen View (if enabled)
    #---------------
    if st.session_state.fullscreen and st.session_state.processed_images:
        show_fullscreen_image()

    # ---------------
    # Bottom Buttons
    # ---------------
    col_save, col_download, col_toggle = st.columns(3)

    with col_save:
        if st.button("Save Edits in Memory"):
            # Save current edited text
            if st.session_state.processed_outputs and st.session_state.processed_images:
                save_current_output_in_session()

            # Rebuild final output
            st.session_state.final_output = ""
            for out in st.session_state.processed_outputs:
                st.session_state.final_output += out + "\n" + ("=" * 50) + "\n"

            st.success("Edits saved in memory! You can now download below.")

    with col_download:
        from datetime import datetime
        timestamp_str = datetime.now().strftime("%m_%d_%y-%I_%M%p")
        timestamped_filename = f"Transcription_Output_{timestamp_str}.txt"

        st.download_button(
            label="Download Output",
            data=st.session_state.final_output,
            file_name=timestamped_filename,
            mime="text/plain",
            help="Save the combined output file to your local machine"
        )

    with col_toggle:
        if st.button("Toggle Theme"):
            st.info("Theme toggling is not supported in Streamlit as in Tkinter. (Placeholder only.)")

    # Show final combined output
    st.write("### Final Output (Combined)")
    st.text_area("Combined Output:", st.session_state.final_output, height=200)


def save_current_output_in_session():
    """
    Helper: saves any text changes in the text area to session state.
    """
    if "processed_outputs" in st.session_state and "output_text_area" in st.session_state:
        idx = st.session_state.current_image_index
        if idx < len(st.session_state.processed_outputs):
            st.session_state.processed_outputs[idx] = st.session_state.output_text_area


def show_fullscreen_image():
    """
    Displays the current image in a 'full screen' style overlay or section,
    plus a button to close it.
    """
    st.write("## Full-Screen Image Viewer")
    idx = st.session_state.current_image_index
    image = st.session_state.processed_images[idx]

    # You can tweak size or use a third-party zoom library
    st.image(image, caption=f"Full Screen of Image {idx + 1}", use_container_width=True)

    # Close button
    if st.button("Close Full Screen"):
        st.session_state.fullscreen = False
        st.experimental_rerun()


if __name__ == "__main__":
    main()
