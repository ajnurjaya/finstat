import os
from pathlib import Path
from typing import Dict, List
import PyPDF2
import pdfplumber
from docx import Document
import io


class DocumentParser:
    """Parse different document formats and extract text content"""

    @staticmethod
    def parse_pdf(file_path: str) -> Dict[str, any]:
        """Extract text from PDF using PyPDF2 and pdfplumber for better accuracy"""
        text_content = []

        try:
            # Try pdfplumber first (better for complex PDFs)
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append({
                            "page": page_num,
                            "text": page_text.strip()
                        })

            full_text = "\n\n".join([page["text"] for page in text_content])

            return {
                "success": True,
                "text": full_text,
                "pages": text_content,
                "page_count": len(text_content),
                "format": "pdf"
            }
        except Exception as e:
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append({
                                "page": page_num,
                                "text": page_text.strip()
                            })

                full_text = "\n\n".join([page["text"] for page in text_content])

                return {
                    "success": True,
                    "text": full_text,
                    "pages": text_content,
                    "page_count": len(text_content),
                    "format": "pdf"
                }
            except Exception as e2:
                return {
                    "success": False,
                    "error": f"PDF parsing failed: {str(e2)}",
                    "format": "pdf"
                }

    @staticmethod
    def parse_docx(file_path: str) -> Dict[str, any]:
        """Extract text from DOCX files"""
        try:
            doc = Document(file_path)
            paragraphs = []

            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text.strip())

            # Also extract text from tables
            tables_text = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells])
                    if row_text.strip():
                        tables_text.append(row_text)

            full_text = "\n\n".join(paragraphs)
            if tables_text:
                full_text += "\n\n=== TABLES ===\n\n" + "\n".join(tables_text)

            return {
                "success": True,
                "text": full_text,
                "paragraphs": paragraphs,
                "tables_found": len(doc.tables),
                "format": "docx"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"DOCX parsing failed: {str(e)}",
                "format": "docx"
            }

    @staticmethod
    def parse_txt(file_path: str) -> Dict[str, any]:
        """Extract text from TXT files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()

            return {
                "success": True,
                "text": text.strip(),
                "format": "txt"
            }
        except UnicodeDecodeError:
            # Try different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    text = file.read()

                return {
                    "success": True,
                    "text": text.strip(),
                    "format": "txt",
                    "encoding": "latin-1"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"TXT parsing failed: {str(e)}",
                    "format": "txt"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"TXT parsing failed: {str(e)}",
                "format": "txt"
            }

    @staticmethod
    def parse_document(file_path: str) -> Dict[str, any]:
        """Main method to parse any supported document format"""
        file_extension = Path(file_path).suffix.lower()

        if file_extension == '.pdf':
            return DocumentParser.parse_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return DocumentParser.parse_docx(file_path)
        elif file_extension == '.txt':
            return DocumentParser.parse_txt(file_path)
        else:
            return {
                "success": False,
                "error": f"Unsupported file format: {file_extension}",
                "format": file_extension
            }
