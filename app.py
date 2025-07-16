import streamlit as st
from dotenv import load_dotenv; load_dotenv()
import io
import os
import json
from utils import extract_text_from_pdf, extract_text_from_docx
from llm_agents import analyze_sow_structured, summarize_sow_detailed, draft_technical_proposal

# --- Configuration ---
# Choose your LLM provider: "openai" or "gemini"
LLM_CHOICE = "openai" # <--- IMPORTANT: SET YOUR LLM CHOICE HERE!

# --- Streamlit App ---
st.set_page_config(layout="wide", page_title="SOW-to-Proposal AI Assistant")

st.title("📄 SOW-to-Proposal AI Assistant (MVP)")
st.markdown("Upload your Scope of Work (SOW) document to get a detailed summary and a draft technical proposal.")

# File Uploader
uploaded_file = st.file_uploader("Upload SOW (PDF or DOCX)", type=["pdf", "docx"])

sow_text = ""
if uploaded_file is not None:
    file_extension = uploaded_file.name.split(".")[-1].lower()
    file_buffer = io.BytesIO(uploaded_file.getvalue())

    with st.spinner("Extracting text from SOW..."):
        if file_extension == "pdf":
            sow_text = extract_text_from_pdf(file_buffer)
        elif file_extension == "docx":
            sow_text = extract_text_from_docx(file_buffer)
        else:
            st.error("Unsupported file type. Please upload a PDF or DOCX.")
            sow_text = ""

    if sow_text:
        st.success("Text extracted successfully!")
        st.expander("View Raw Extracted Text").text_area("Raw SOW Text", sow_text, height=300)
    else:
        st.error("Could not extract text from the uploaded SOW document.")

# --- SOW Analysis & Summary ---
if sow_text:
    st.subheader("🎯 SOW Analysis & Detailed Summary")

    # Analyze SOW into structured data
    if st.button("Analyze SOW"):
        with st.spinner("Analyzing SOW details with AI..."):
            sow_structured_data = analyze_sow_structured(sow_text, llm_choice=LLM_CHOICE)
            if sow_structured_data and not sow_structured_data.get("error"):
                st.session_state['sow_structured_data'] = sow_structured_data
                st.success("SOW analysis complete!")
            else:
                st.error(f"Failed to analyze SOW: {sow_structured_data.get('error', 'Unknown error.')}")

    if 'sow_structured_data' in st.session_state and not st.session_state['sow_structured_data'].get("error"):
        sow_data = st.session_state['sow_structured_data']

        # Display Structured SOW Data (Dashboard View)
        st.markdown("#### Structured SOW Insights")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Project Name:** {sow_data.get('project_name', 'N/A')}")
            st.info(f"**Client Name:** {sow_data.get('client_name', 'N/A')}")
            st.json(sow_data.get("objectives", []))
            st.json(sow_data.get("technical_requirements", []))

        with col2:
            st.json(sow_data.get("deliverables", []))
            st.json(sow_data.get("key_constraints", []))
            st.json(sow_data.get("timeline_overview", "N/A"))
            st.json(sow_data.get("stakeholders", []))

        st.markdown("---")
        st.markdown("#### Detailed Narrative Summary")
        with st.spinner("Generating detailed narrative summary..."):
            detailed_summary = summarize_sow_detailed(sow_data, llm_choice=LLM_CHOICE)
            st.write(detailed_summary)
        st.markdown("---")

        # --- Draft Technical Proposal ---
        st.subheader("✍️ Draft Technical Proposal")
        if st.button("Generate Technical Proposal Draft"):
            with st.spinner("Drafting technical proposal with AI..."):
                proposal_draft = draft_technical_proposal(sow_data, llm_choice=LLM_CHOICE)
                st.session_state['proposal_draft'] = proposal_draft
                st.success("Technical proposal draft generated!")

        if 'proposal_draft' in st.session_state:
            st.markdown("#### Generated Draft")
            st.markdown(st.session_state['proposal_draft'])
            st.download_button(
                label="Download Proposal Draft (Markdown)",
                data=st.session_state['proposal_draft'],
                file_name="technical_proposal_draft.md",
                mime="text/markdown"
            )
            st.button("Copy Proposal Draft", on_click=lambda: st.experimental_set_query_params(copy=st.session_state['proposal_draft']))
            if st.experimental_get_query_params().get("copy"):
                st.success("Draft copied to clipboard (check your browser's clipboard access)!")