# 📄 SOW-to-Proposal AI Assistant (MVP)

## Project Overview

The "SOW-to-Proposal AI Assistant" is a Minimum Viable Product (MVP) designed to streamline the initial stages of technical proposal drafting. It automates the analysis of a client's Scope of Work (SOW) document, provides a structured summary on a dashboard, and generates a preliminary draft of a technical proposal. This tool aims to significantly reduce the manual effort and time typically spent by Business Development Teams, Solution Architects, and Bid Managers in understanding client requirements and initiating proposal responses.

## ✨ Features (MVP)

* **SOW Document Ingestion:** Upload PDF or DOCX SOW documents directly via a user-friendly web interface.
* **Intelligent SOW Analysis:** AI agents powered by large language models (LLMs) parse the SOW to extract key information, including:
    * Project Name, Client Name
    * Project Objectives
    * Detailed Scope of Work (Included/Excluded)
    * Key Deliverables
    * Technical Requirements
    * Constraints, Stakeholders, and Timeline Overview
* **Interactive SOW Dashboard:** Presents the extracted SOW insights in a clear, structured dashboard format for quick review and validation.
* **Detailed SOW Summary:** Generates a comprehensive natural language summary of the SOW.
* **Technical Proposal Draft Generation:** Creates an initial draft of a technical proposal (in Markdown format) based directly on the SOW analysis, covering essential sections like Executive Summary, Proposed Solution, Deliverables, and Timeline.
* **Download & Copy Options:** Allows users to easily download the generated proposal draft or copy it for further editing.

## 🚀 Technologies Used

* **Python:** The core programming language.
* **Streamlit:** For building the interactive web-based user interface rapidly.
* **PyPDF2:** For extracting text from PDF documents.
* **python-docx:** For extracting text from Microsoft Word (.docx) documents.
* **OpenAI API / Google Gemini API:** For powering the large language models (LLMs) that perform SOW analysis, summarization, and proposal drafting.
* **python-dotenv:** (Optional, for local development) To manage API keys securely via a `.env` file.

## 📦 Project Structure