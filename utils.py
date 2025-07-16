import io
from PyPDF2 import PdfReader
from docx import Document

def extract_text_from_pdf(file_buffer: io.BytesIO) -> str:
    """Extracts text from a PDF file buffer."""
    try:
        reader = PdfReader(file_buffer)
        text = ""
        for page_num in range(len(reader.pages)):
            text += reader.pages[page_num].extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(file_buffer: io.BytesIO) -> str:
    """Extracts text from a DOCX file buffer."""
    try:
        document = Document(file_buffer)
        text = ""
        for para in document.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""