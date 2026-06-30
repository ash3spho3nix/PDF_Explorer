"""
Extracts textual components out of structural initial page headers.
"""

import pypdf


class FirstPageExtractor:
    """Inspects text elements on the first page of a document to drive rule-based keyword sorting."""

    def extract(self, pdf_path: str) -> str:
        """
        Grabs textual streams from the first page of a PDF document.
        """
        try:
            with open(pdf_path, "rb") as stream:
                reader = pypdf.PdfReader(stream)
                
                if reader.is_encrypted or len(reader.pages) == 0:
                    return ""
                
                first_page = reader.pages[0]
                extracted_text = first_page.extract_text()
                
                return extracted_text if extracted_text else ""
        except Exception:
            return ""