# --- utils.py ---
# This file contains helper functions for document parsing.

import io
from PyPDF2 import PdfReader
from docx import Document

def extract_text_from_pdf(file_buffer: io.BytesIO) -> str:
    """
    Extracts text from a PDF file buffer.
    Args:
        file_buffer (io.BytesIO): The buffer of the PDF file.
    Returns:
        str: The extracted text content.
    """
    try:
        reader = PdfReader(file_buffer)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() if page.extract_text() else "" # Handle potentially empty pages
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(file_buffer: io.BytesIO) -> str:
    """
    Extracts text from a DOCX file buffer.
    Args:
        file_buffer (io.BytesIO): The buffer of the DOCX file.
    Returns:
        str: The extracted text content.
    """
    try:
        document = Document(file_buffer)
        text = ""
        for para in document.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""