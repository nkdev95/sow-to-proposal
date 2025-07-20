# --- app.py ---
# This is the main Streamlit application file.
# It orchestrates UI, file handling, and calls to LLM agents.

import streamlit as st
import io
import os
import json

# --- IMPORTANT: Load environment variables from .env file ---
# Ensure python-dotenv is installed (pip install python-dotenv)
# and your .env file is in the project root.
from dotenv import load_dotenv
load_dotenv() # This line loads the variables from .env

# Import helper functions and LLM agents
# Assuming utils.py and llm_agents.py are in the same directory
import utils
import llm_agents

# --- Configuration ---
# Set LLM provider to "gemini" as requested.
# Make sure the corresponding API key (GOOGLE_API_KEY) is set in your .env file.
LLM_CHOICE = "gemini" # <--- IMPORTANT: LLM CHOICE IS NOW FIXED TO GEMINI!


# Initialize LLM clients in llm_agents.py based on the choice
# This block ensures API keys are loaded and clients are set up before LLM calls.
if LLM_CHOICE == "gemini":
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        llm_agents.genai.configure(api_key=api_key)
        llm_agents.gemini_model = llm_agents.genai.GenerativeModel('gemini-1.5-flash') # Or 'gemini-1.5-pro'
    else:
        st.error("Google Gemini API Key not found. Please set GOOGLE_API_KEY in your .env file.")
else:
    # This else block should ideally not be reached if LLM_CHOICE is fixed to "gemini"
    st.error(f"Invalid LLM_CHOICE: {LLM_CHOICE}. This application is configured for Gemini only.")


# --- Streamlit App Layout ---
st.set_page_config(layout="wide", page_title="SOW-to-Proposal AI Assistant")

st.title("📄 SOW-to-Proposal AI Assistant (MVP)")
st.markdown("Upload your Scope of Work (SOW) document to get a detailed summary and a draft technical proposal.")
st.markdown(f"*(Using {LLM_CHOICE.capitalize()} for AI generation)*")

# --- File Uploader Section ---
st.header("1. Upload Your Scope of Work (SOW)")
uploaded_file = st.file_uploader("Select a PDF or DOCX file", type=["pdf", "docx"])

sow_text = ""
if uploaded_file is not None:
    file_extension = uploaded_file.name.split(".")[-1].lower()
    file_buffer = io.BytesIO(uploaded_file.getvalue())

    with st.spinner("Extracting text from SOW... This may take a moment for larger files."):
        if file_extension == "pdf":
            sow_text = utils.extract_text_from_pdf(file_buffer)
        elif file_extension == "docx":
            sow_text = utils.extract_text_from_docx(file_buffer)
        else:
            st.error("Unsupported file type. Please upload a PDF or DOCX.")
            sow_text = ""

    if sow_text:
        st.success("Text extracted successfully!")
        with st.expander("View Raw Extracted Text (Click to expand)"):
            st.text_area("Raw SOW Text", sow_text, height=300, disabled=True)
    else:
        st.error("Could not extract text from the uploaded SOW document. Please ensure it's a readable PDF or DOCX.")

# --- SOW Analysis & Summary Section ---
if sow_text:
    st.header("2. Analyze SOW & Get Summary")

    # Button to trigger SOW analysis
    if st.button("Analyze SOW Details", key="analyze_sow_btn"):
        if not sow_text:
            st.warning("Please upload an SOW document first.")
        else:
            # Check if LLM client is initialized before calling
            if not llm_agents.gemini_model: # Only check for gemini_model as LLM_CHOICE is fixed
                st.error("Gemini LLM client not properly initialized. Please check your API key setup in .env.")
            else:
                with st.spinner("Analyzing SOW details with AI... This might take a minute."):
                    sow_structured_data = llm_agents.analyze_sow_structured(sow_text, llm_choice=LLM_CHOICE)
                    if sow_structured_data and not sow_structured_data.get("error"):
                        st.session_state['sow_structured_data'] = sow_structured_data
                        st.success("SOW analysis complete!")
                    else:
                        st.error(f"Failed to analyze SOW: {sow_structured_data.get('error', 'Unknown error.')}")
                        st.session_state['sow_structured_data'] = None # Clear state on error

    # Display SOW Analysis Dashboard
    if 'sow_structured_data' in st.session_state and st.session_state['sow_structured_data'] and \
       not st.session_state['sow_structured_data'].get("error"):
        sow_data = st.session_state['sow_structured_data']

        st.markdown("### 📊 Structured SOW Insights Dashboard")
        col1, col2 = st.columns(2)

        with col1:
            st.info(f"**Project Name:** {sow_data.get('project_name', 'N/A')}")
            st.info(f"**Client Name:** {sow_data.get('client_name', 'N/A')}")
            st.markdown(f"**Objectives:**")
            if sow_data.get("objectives"):
                for obj in sow_data["objectives"]:
                    st.markdown(f"- {obj}")
            else:
                st.markdown("- N/A")
            st.markdown(f"**Technical Requirements:**")
            if sow_data.get("technical_requirements"):
                for tech in sow_data["technical_requirements"]:
                    st.markdown(f"- {tech}")
            else:
                st.markdown("- N/A")

        with col2:
            st.markdown(f"**Deliverables:**")
            if sow_data.get("deliverables"):
                for d in sow_data["deliverables"]:
                    st.markdown(f"- **{d.get('name', 'N/A')}**: {d.get('description', 'N/A')}")
            else:
                st.markdown("- N/A")
            st.markdown(f"**Key Constraints:**")
            if sow_data.get("key_constraints"):
                for constr in sow_data["key_constraints"]:
                    st.markdown(f"- {constr}")
            else:
                st.markdown("- N/A")
            st.info(f"**Timeline Overview:** {sow_data.get('timeline_overview', 'N/A')}")
            st.markdown(f"**Stakeholders:**")
            if sow_data.get("stakeholders"):
                for stakeholder in sow_data["stakeholders"]:
                    st.markdown(f"- {stakeholder}")
            else:
                st.markdown("- N/A")

        st.markdown("---")
        st.markdown("### 📝 Detailed Narrative Summary of SOW")
        with st.spinner("Generating detailed narrative summary..."):
            detailed_summary = llm_agents.summarize_sow_detailed(sow_data, llm_choice=LLM_CHOICE)
            st.write(detailed_summary)
        st.markdown("---")

        # --- Draft Technical Proposal Section ---
        st.header("3. Generate Technical Proposal Draft")
        if st.button("Generate Proposal Draft", key="generate_proposal_btn"):
            # Check if LLM client is initialized before calling
            if not llm_agents.gemini_model: # Only check for gemini_model as LLM_CHOICE is fixed
                st.error("Gemini LLM client not properly initialized. Please check your API key setup in .env.")
            else:
                with st.spinner("Drafting technical proposal with AI... This will take a moment."):
                    proposal_draft = llm_agents.draft_technical_proposal(sow_data, llm_choice=LLM_CHOICE)
                    st.session_state['proposal_draft'] = proposal_draft
                    st.success("Technical proposal draft generated!")

        if 'proposal_draft' in st.session_state and st.session_state['proposal_draft']:
            st.markdown("### ✍️ Your Generated Proposal Draft")
            st.markdown(st.session_state['proposal_draft'])

            # Buttons for download and copy
            col_dl, col_copy = st.columns(2)
            with col_dl:
                st.download_button(
                    label="Download Proposal Draft (Markdown)",
                    data=st.session_state['proposal_draft'],
                    file_name="technical_proposal_draft.md",
                    mime="text/markdown"
                )
            with col_copy:
                # Streamlit does not have direct clipboard access in browser context for security.
                # Provide a text area for easy manual copying.
                st.text_area("Copy Proposal Draft (Manual Copy)", st.session_state['proposal_draft'], height=200, help="Select all text and copy manually.")
                st.info("For security reasons, direct 'Copy to Clipboard' is not available in Streamlit. Please manually select and copy the text from the box above.")

else:
    st.warning("Please upload an SOW document first.")  # Placeholder   