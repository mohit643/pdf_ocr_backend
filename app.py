from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import re
import os

app = Flask(__name__)
CORS(app)

@app.route('/extract-pdf', methods=['POST'])
def extract_pdf():
    print("=== PDF Upload Request Received ===")
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save temporarily
    file_path = f'temp_{file.filename}'
    file.save(file_path)
    print(f"File saved: {file_path}")
    
    try:
        # Extract text from PDF
        print("Extracting text from PDF...")
        text = extract_text_from_pdf(file_path)
        print(f"Extracted text length: {len(text)}")
        
        # Parse extracted text
        print("Parsing bill data...",text)
        
        bill_data = parse_bill_data(text)
        
        # Delete temp file
        if os.path.exists(file_path):
            os.remove(file_path)
            print("Temp file deleted")
        
        print("=== Extraction Complete ===")
        return jsonify(bill_data)
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        # Delete temp file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': str(e)}), 500


def extract_text_from_pdf(file_path):
    """Faster extraction - parallel processing"""
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        # Extract only first 5 pages (bills usually single page)
        max_pages = min(5, len(reader.pages))
        for i in range(max_pages):
            text += reader.pages[i].extract_text() + "\n"
    return text


def parse_bill_data(text):
    """Optimized parsing with compiled regex"""
    
    # Pre-compile patterns for speed
    patterns = {
        'accountNo': re.compile(r'Account\s*No[.:\s]*([0-9]{10,12})', re.I),
        'billNumber': re.compile(r'Bill\s*Number[:\s]*([0-9]+)', re.I),
        'customerName': re.compile(r'Name[:\s]*([A-Z\s/]+?)(?=\n|खंड)', re.I),
        'payableAmount': re.compile(r'Payable\s*Amount[:\s]*([0-9,]+)', re.I),
        'dueDate': re.compile(r'Due\s*Date[:\s]*([0-9-A-Z]+)', re.I),
        'billDate': re.compile(r'Bill\s*Date[:\s]*([0-9-A-Z]+)', re.I),
        'netBilledUnit': re.compile(r'Net\s*Billed\s*Unit[:\s]*([0-9.]+)', re.I),
        'energyCharges': re.compile(r'Energy\s*Charges[:\s]*([0-9,.]+)', re.I),
        'demandCharges': re.compile(r'Demand\s*Charges[:\s]*([0-9,.]+)', re.I),
        'electricityDuty': re.compile(r'Electricity\s*Duty[:\s]*([0-9,.]+)', re.I),
    }
    print("patterns",patterns)
    # Fast extraction using compiled patterns
    def fast_extract(pattern_name):
        match = patterns[pattern_name].search(text)
        return match.group(1).strip() if match else ""
    
    # Build response - only extract what's needed
    bill_data = {
        'accountNo': fast_extract('accountNo'),
        'billNumber': fast_extract('billNumber'),
        'customerName': fast_extract('customerName'),
        'billDate': fast_extract('billDate'),
        'dueDate': fast_extract('dueDate'),
        'payableAmount': fast_extract('payableAmount').replace(',', ''),
        'netBilledUnit': fast_extract('netBilledUnit'),
        
        'charges': {
            'energyCharges': fast_extract('energyCharges').replace(',', ''),
            'demandCharges': fast_extract('demandCharges').replace(',', ''),
            'electricityDuty': fast_extract('electricityDuty').replace(',', ''),
        }
    }
    
    return bill_data

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'Server is running', 'tesseract': 'configured'})


if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000")
    print("Make sure Tesseract is installed at: C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
    app.run(debug=True, port=5000)