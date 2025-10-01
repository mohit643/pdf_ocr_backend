"""
PDF Service - All PDF operations
Save as: backend/services/pdf_service.py
"""

import fitz  # PyMuPDF
import base64
from typing import List, Dict, Optional
from pathlib import Path


class PDFService:
    """Service for PDF processing operations"""
    
    @staticmethod
    def get_pdf_info(pdf_path: str) -> Dict:
        """Get basic PDF information"""
        try:
            doc = fitz.open(pdf_path)
            info = {
                'total_pages': len(doc),
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'file_size': Path(pdf_path).stat().st_size
            }
            doc.close()
            return info
        except Exception as e:
            raise Exception(f"Failed to get PDF info: {str(e)}")
    
    @staticmethod
    def extract_text_with_positions(pdf_path: str, page_num: int) -> List[Dict]:
        """Extract text blocks with their exact positions"""
        try:
            doc = fitz.open(pdf_path)
            
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} does not exist")
            
            page = doc[page_num]
            text_dict = page.get_text("dict")
            text_blocks = []
            
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_blocks.append({
                                'text': span['text'],
                                'bbox': span['bbox'],
                                'font': span['font'],
                                'size': span['size'],
                                'color': span.get('color', 0),
                                'flags': span.get('flags', 0)
                            })
            
            doc.close()
            return text_blocks
            
        except Exception as e:
            print(f"Error extracting text: {e}")
            return []
    
    @staticmethod
    def render_page_as_image(
        pdf_path: str, 
        page_num: int, 
        zoom: float = 2.0
    ) -> Optional[Dict]:
        """Render PDF page as base64 image"""
        try:
            doc = fitz.open(pdf_path)
            
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} does not exist")
            
            page = doc[page_num]
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            img_bytes = pix.tobytes("png")
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            result = {
                'image': f'data:image/png;base64,{img_base64}',
                'width': pix.width,
                'height': pix.height,
                'original_width': page.rect.width,
                'original_height': page.rect.height
            }
            
            doc.close()
            return result
            
        except Exception as e:
            print(f"Error rendering page: {e}")
            return None
    
    @staticmethod
    def apply_text_edits(
        pdf_path: str, 
        edits: List[Dict], 
        output_path: str
    ) -> bool:
        """Apply text edits to PDF"""
        try:
            doc = fitz.open(pdf_path)
            
            for edit in edits:
                page_num = edit.get('page', 0)
                
                if page_num >= len(doc):
                    continue
                
                page = doc[page_num]
                bbox = edit['bbox']
                new_text = edit['new_text']
                font_size = edit.get('fontSize', 12)
                color = edit.get('color', '#000000')
                
                rect = fitz.Rect(bbox)
                
                # Remove old text
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
                
                # Parse color
                if isinstance(color, str):
                    color = color.lstrip('#')
                    rgb_color = tuple(int(color[i:i+2], 16) / 255 for i in (0, 2, 4))
                else:
                    rgb_color = (0, 0, 0)
                
                # Insert new text
                point = fitz.Point(rect.x0, rect.y0 + font_size)
                page.insert_text(
                    point,
                    new_text,
                    fontsize=font_size,
                    color=rgb_color,
                    fontname="helv"
                )
            
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()
            
            return True
            
        except Exception as e:
            print(f"Error applying edits: {e}")
            return False
    
    @staticmethod
    def search_text(pdf_path: str, search_term: str) -> List[Dict]:
        """Search for text in PDF"""
        try:
            doc = fitz.open(pdf_path)
            results = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_instances = page.search_for(search_term)
                
                for bbox in text_instances:
                    results.append({
                        'page': page_num,
                        'bbox': list(bbox),
                        'text': search_term
                    })
            
            doc.close()
            return results
            
        except Exception as e:
            print(f"Error searching text: {e}")
            return []