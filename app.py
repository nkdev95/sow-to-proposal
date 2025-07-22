# --- app.py ---
# This is the main Streamlit application file.
# It orchestrates UI, file handling, and calls to LLM agents.

import streamlit as st
import io
import os
import json
import pandas as pd # Import pandas for DataFrame display
import plotly.express as px # For potential future graphs, though not heavily used in this MVP

# --- IMPORTANT: Load environment variables from .env file ---
# Ensure python-dotenv is installed (pip install python-dotenv)
# and your .env file is in the project root.
from dotenv import load_dotenv
load_dotenv() # This line loads the variables from .env

# Import helper functions and LLM agents
import utils
import llm_agents

# --- Streamlit App Configuration (MUST BE THE FIRST STREAMLIT COMMANDS) ---
st.set_page_config(layout="wide", page_title="SOW-to-Proposal AI Assistant")

st.title("📄 SOW-to-Proposal AI Assistant (MVP)")
st.markdown("Upload your Scope of Work (SOW) document to get a detailed summary and a draft technical proposal.")

# --- Configuration ---
# Choose your LLM provider: "openai" or "gemini"
# Make sure the corresponding API key is set in your .env file
LLM_CHOICE = "gemini" # <--- IMPORTANT: LLM CHOICE IS NOW FIXED TO OPENAI!

# Display which LLM is being used in the main content area
st.markdown(f"*(Using {LLM_CHOICE.capitalize()} for AI generation)*")

# Initialize LLM clients only if API keys are available and selected
llm_agents.openai_client = None
llm_agents.gemini_model = None

# Initialize LLM clients in llm_agents.py based on the choice
# This block ensures API keys are loaded and clients are set up before LLM calls.
if LLM_CHOICE == "openai":
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        llm_agents.openai_client = llm_agents.OpenAI(api_key=api_key)
    else:
        st.error("OpenAI API Key not found. Please set OPENAI_API_KEY in your .env file.")
        st.stop() # Stop execution if API key is missing
elif LLM_CHOICE == "gemini": # This branch will not be taken as LLM_CHOICE is "openai"
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        llm_agents.genai.configure(api_key=api_key)
        llm_agents.gemini_model = llm_agents.genai.GenerativeModel('gemini-2.5-flash') # Or 'gemini-1.5-pro'
    else:
        st.error("Google Gemini API Key not found. Please set GOOGLE_API_KEY in your .env file.")
        st.stop() # Stop execution if API key is missing
else:
    st.error(f"Invalid LLM_CHOICE: {LLM_CHOICE}. This application is configured for OpenAI or Gemini.")
    st.stop() # Stop execution if LLM_CHOICE is invalid

# Function to clear session state for a fresh start
def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

st.sidebar.button("🔄 Start Fresh / Reset", on_click=reset_app)


# --- File Uploader Section ---
st.header("1. Upload Your Scope of Work (SOW)")
uploaded_file = st.file_uploader("Select a PDF or DOCX file", type=["pdf", "docx"])

sow_text = ""
if uploaded_file is not None:
    file_extension = uploaded_file.name.split(".")[-1].lower()
    file_buffer = io.BytesIO(uploaded_file.getvalue())

    with st.spinner("🚀 Extracting text from SOW... This may take a moment for larger files."):
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
            # Check if the selected LLM client is initialized
            if (LLM_CHOICE == "openai" and not llm_agents.openai_client) or \
               (LLM_CHOICE == "gemini" and not llm_agents.gemini_model):
                st.error(f"{LLM_CHOICE.capitalize()} LLM client not properly initialized. Please check your API key setup in .env.")
            else:
                with st.spinner("🧠 Analyzing SOW details with AI... This might take a minute."):
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
        st.info("Here's a quick overview of the key information extracted from your SOW, organized for clarity.")

        # --- Dashboard Tabs ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Scope", "Deliverables", "Technical", "Constraints & Stakeholders"])

        with tab1:
            st.subheader("Project Overview")
            col_proj_name, col_client_name, col_timeline = st.columns(3)
            with col_proj_name:
                st.metric("Project Name", sow_data.get('project_name', 'N/A'))
            with col_client_name:
                st.metric("Client Name", sow_data.get('client_name', 'N/A'))
            with col_timeline:
                # Display timeline as a joined string for metric, or list in detail section
                timeline_overview = sow_data.get('timeline_overview', 'N/A')
                st.metric("Timeline Overview", str(timeline_overview))

            st.markdown("---")
            st.markdown("#### Key Objectives")
            if sow_data.get("objectives"):
                for i, obj in enumerate(sow_data["objectives"]):
                    st.markdown(f"**{i+1}.** {obj}")
            else:
                st.markdown("- No specific objectives identified.")
            
            # Simple bar chart for count of objectives
            if sow_data.get("objectives"):
                obj_count_df = pd.DataFrame({'Category': ['Key Objectives'], 'Count': [len(sow_data["objectives"])]})
                fig = px.bar(obj_count_df, x='Category', y='Count', title='Number of Key Objectives Identified', text='Count',
                             color_discrete_sequence=['#28a745']) # Green color
                fig.update_traces(texttemplate='%{text}', textposition='outside')
                fig.update_layout(xaxis_title="", yaxis_title="Count", showlegend=False, yaxis_range=[0, max(5, len(sow_data["objectives"]) + 1)]) # Ensure y-axis starts from 0
                st.plotly_chart(fig, use_container_width=True)


        with tab2:
            st.subheader("Scope Definition")
            col_scope_in, col_scope_out = st.columns(2)
            with col_scope_in:
                st.markdown("**Included Scope of Work:**")
                if sow_data.get("scope_of_work"):
                    for i, item in enumerate(sow_data["scope_of_work"]):
                        st.markdown(f"**{i+1}.** {item}")
                else:
                    st.markdown("- No detailed included scope identified.")
            with col_scope_out:
                st.markdown("**Out of Scope:**")
                if sow_data.get("out_of_scope"):
                    for i, item in enumerate(sow_data["out_of_scope"]):
                        st.markdown(f"**{i+1}.** {item}")
                else:
                    st.markdown("- No specific out-of-scope items identified.")

            # Simple Pie chart for scope distribution (example)
            scope_counts = {'Included Scope': len(sow_data.get("scope_of_work", [])),
                            'Out of Scope': len(sow_data.get("out_of_scope", []))}
            if sum(scope_counts.values()) > 0:
                scope_df = pd.DataFrame(list(scope_counts.items()), columns=['Category', 'Count'])
                fig_pie = px.pie(scope_df, values='Count', names='Category', title='Scope Items Distribution',
                                 color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_pie, use_container_width=True)


        with tab3:
            st.subheader("Key Deliverables")
            if sow_data.get("deliverables"):
                # Ensure deliverables are in a suitable format for DataFrame
                # Handle cases where LLM might return non-dict items in deliverables list
                cleaned_deliverables = []
                for item in sow_data["deliverables"]:
                    if isinstance(item, dict) and "name" in item and "description" in item:
                        cleaned_deliverables.append(item)
                    elif isinstance(item, str): # Handle if LLM returned list of strings
                         cleaned_deliverables.append({"name": item, "description": "Not detailed by AI"})
                
                if cleaned_deliverables:
                    deliverables_df = pd.DataFrame(cleaned_deliverables)
                    st.dataframe(deliverables_df, use_container_width=True, hide_index=True)
                else:
                    st.markdown("- No specific deliverables identified or could not be parsed into a table.")
            else:
                st.markdown("- No specific deliverables identified.")

        with tab4:
            st.subheader("Technical Landscape")
            st.markdown("**Technical Requirements:**")
            if sow_data.get("technical_requirements"):
                for i, tech in enumerate(sow_data["technical_requirements"]):
                    st.markdown(f"**{i+1}.** {tech}")
            else:
                st.markdown("- No specific technical requirements identified.")
            
            # Bar chart for number of technical requirements
            if sow_data.get("technical_requirements"):
                tech_count_df = pd.DataFrame({'Category': ['Technical Requirements'], 'Count': [len(sow_data["technical_requirements"])]})
                fig = px.bar(tech_count_df, x='Category', y='Count', title='Number of Technical Requirements Identified', text='Count',
                             color_discrete_sequence=['#17a2b8']) # Info color
                fig.update_traces(texttemplate='%{text}', textposition='outside')
                fig.update_layout(xaxis_title="", yaxis_title="Count", showlegend=False, yaxis_range=[0, max(5, len(sow_data["technical_requirements"]) + 1)])
                st.plotly_chart(fig, use_container_width=True)

        with tab5:
            st.subheader("Constraints & Key Stakeholders")
            col_constr, col_stake_detail = st.columns(2)
            with col_constr:
                st.markdown("**Key Constraints:**")
                if sow_data.get("key_constraints"):
                    for i, constr in enumerate(sow_data["key_constraints"]):
                        st.markdown(f"**{i+1}.** {constr}")
                else:
                    st.markdown("- No specific constraints identified.")
            with col_stake_detail:
                st.markdown("**Key Stakeholders:**")
                if sow_data.get("stakeholders"):
                    for i, stakeholder in enumerate(sow_data["stakeholders"]):
                        st.markdown(f"**{i+1}.** {stakeholder}")
                else:
                    st.markdown("- No specific stakeholders identified.")

        st.markdown("---")
        st.markdown("### 📝 Detailed Narrative Summary of SOW")
        with st.spinner("✍️ Generating detailed narrative summary..."):
            detailed_summary = llm_agents.summarize_sow_detailed(sow_data, llm_choice=LLM_CHOICE)
            st.write(detailed_summary)
        st.markdown("---")

        # --- Draft Technical Proposal Section ---
        st.header("3. Generate Technical Proposal Draft")
        st.info("This will generate a preliminary technical proposal based on the SOW analysis. Remember, this is a draft and requires human review and refinement.")
        if st.button("Generate Proposal Draft", key="generate_proposal_btn"):
            # Check if the selected LLM client is initialized
            if (LLM_CHOICE == "openai" and not llm_agents.openai_client) or \
               (LLM_CHOICE == "gemini" and not llm_agents.gemini_model):
                st.error(f"{LLM_CHOICE.capitalize()} LLM client not properly initialized. Please check your API key setup in .env.")
            else:
                with st.spinner("🤖 Drafting technical proposal with AI... This will take a moment."):
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
                st.text_area("Copy Proposal Draft (Manual Copy)", st.session_state['proposal_draft'], height=200, help="Select all text and copy manually.")
                st.info("For security reasons, direct 'Copy to Clipboard' is not available in Streamlit. Please manually select and copy the text from the box above.")

# --- Footer ---
st.markdown("---")
st.markdown("Built with ❤️ and AI by Your Team.")