"""
PDF Processing Utilities
Complete implementation for text extraction, rendering, and editing
"""
import fitz  # PyMuPDF
import base64
import io
from PIL import Image
from typing import List, Dict, Optional
from schemas import TextEdit, Signature


def extract_text_blocks(pdf_path: str, page_num: int) -> List[Dict]:
    """
    Extract text blocks with positions from PDF page
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
    
    Returns:
        List of text block dictionaries with bbox, font, size, etc.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        text_dict = page.get_text("dict")
        text_blocks = []
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_name = span.get('font', '').lower()
                        flags = span.get('flags', 0)
                        
                        text_blocks.append({
                            'text': span['text'],
                            'bbox': span['bbox'],
                            'font': span['font'],
                            'size': span['size'],
                            'color': span.get('color', 0),
                            'bold': 'bold' in font_name or (flags & 16),
                            'italic': 'italic' in font_name or (flags & 2),
                            'flags': flags
                        })
        
        doc.close()
        return text_blocks
    except Exception as e:
        print(f"Error extracting text from {pdf_path}, page {page_num}: {e}")
        return []


def render_page_as_image(pdf_path: str, page_num: int, zoom: float = 2.0) -> Optional[Dict]:
    """
    Render PDF page as base64 encoded image
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        zoom: Zoom factor (2.0 = 200%)
    
    Returns:
        Dictionary with base64 image, width, and height
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        result = {
            'image': f'data:image/png;base64,{img_base64}',
            'width': pix.width,
            'height': pix.height
        }
        
        doc.close()
        return result
    except Exception as e:
        print(f"Error rendering page {page_num} from {pdf_path}: {e}")
        return None


def save_thumbnail(pdf_path: str, page_num: int, output_path: str) -> bool:
    """
    Save thumbnail of PDF page to file
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        output_path: Path where thumbnail will be saved
    
    Returns:
        True if successful, False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        mat = fitz.Matrix(0.3, 0.3)  # 30% size
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(output_path)
        doc.close()
        return True
    except Exception as e:
        print(f"Error saving thumbnail for page {page_num}: {e}")
        return False


def apply_text_edits(pdf_path: str, edits: List[TextEdit], output_path: str) -> bool:
    """
    Apply text edits to PDF
    
    Args:
        pdf_path: Path to input PDF file
        edits: List of TextEdit objects
        output_path: Path where edited PDF will be saved
    
    Returns:
        True if successful, False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        
        for edit in edits:
            page = doc[edit.page]
            rect = fitz.Rect(edit.bbox)
            
            # Remove old text by redacting
            page.add_redact_annot(rect, fill=(1, 1, 1))  # White fill
            page.apply_redactions()
            
            # Parse color
            color = (0, 0, 0)  # Default black
            if edit.color:
                hex_color = edit.color.lstrip('#')
                color = tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
            
            # Insert new text
            point = fitz.Point(rect.x0, rect.y0 + edit.fontSize)
            page.insert_text(
                point, 
                edit.new_text, 
                fontsize=edit.fontSize, 
                color=color
            )
        
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return True
    except Exception as e:
        print(f"Error applying text edits: {e}")
        return False


def apply_signatures(pdf_path: str, signatures: List[Signature], output_path: str) -> bool:
    """
    Apply signature images to PDF
    
    Args:
        pdf_path: Path to input PDF file
        signatures: List of Signature objects
        output_path: Path where PDF with signatures will be saved
    
    Returns:
        True if successful, False otherwise
    """
    if len(signatures) == 0:
        return True
    
    try:
        doc = fitz.open(pdf_path)
        
        for idx, sig in enumerate(signatures):
            try:
                page = doc[sig.page]
                
                # Extract base64 image data
                img_data = sig.image
                if 'base64,' in img_data:
                    img_data = img_data.split('base64,')[1]
                
                # Decode and process image
                img_bytes = base64.b64decode(img_data)
                img = Image.open(io.BytesIO(img_bytes))
                
                # Convert to RGB if needed
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Convert back to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_bytes_final = img_byte_arr.getvalue()
                
                # Insert signature into PDF
                rect = fitz.Rect(sig.x, sig.y, sig.x + sig.width, sig.y + sig.height)
                page.insert_image(rect, stream=img_bytes_final)
                
            except Exception as e:
                print(f"Failed to apply signature {idx + 1}: {e}")
                continue
        
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return True
        
    except Exception as e:
        print(f"Error applying signatures: {e}")
        return False


def get_pdf_info(pdf_path: str) -> Optional[Dict]:
    """
    Get basic information about PDF file
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Dictionary with page count, file size, metadata
    """
    try:
        doc = fitz.open(pdf_path)
        info = {
            'page_count': len(doc),
            'metadata': doc.metadata,
            'is_encrypted': doc.is_encrypted,
            'needs_pass': doc.needs_pass,
        }
        doc.close()
        return info
    except Exception as e:
        print(f"Error getting PDF info: {e}")
        return None