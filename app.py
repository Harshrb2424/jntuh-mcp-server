import os
import re
import time
import uuid
import pandas as pd
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
import requests
from weasyprint import HTML
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DATA_DIR = os.path.join(BASE_DIR, 'results_data')
CSV_FILE = os.path.join(RESULTS_DATA_DIR, 'jntuh_results.csv')
PDF_DIR = os.path.join(BASE_DIR, 'static', 'pdfs')

# Ensure directories exist
os.makedirs(RESULTS_DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Load results data
try:
    if not os.path.exists(CSV_FILE):
        # Create a sample CSV if it doesn't exist
        sample_data = """Title,URL,Exam_Date,degree,examCode,etype,type,result,grad,Regulation,Is_Supplementary,Exam_Type,Year,Semester
B.Tech IV Year I Semester (R18) Supplementary JUNE-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1866&etype=r17&type=intgrade,08-AUGUST-2025,btech,1866,r17,intgrade,,,R18,Yes,Supplementary,IV,I
B.Tech IV Year I Semester (R16) Supplementary JUNE-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1867&etype=r17&type=intgrade,08-AUGUST-2025,btech,1867,r17,intgrade,,,R16,Yes,Supplementary,IV,I
B.Tech IV Year I Semester (R15) Supplementary JUNE-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1868,08-AUGUST-2025,btech,1868,,,,,R15,Yes,Supplementary,IV,I
B.Tech IV Year I Semester (R18) (Minor degree) Supplementary JUNE-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1869&etype=r17&type=intgrade,08-AUGUST-2025,btech,1869,r17,intgrade,,,R18,Yes,Supplementary,IV,I
B.Pharmacy IV Year I Semester (R18) Regular JAN-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=bpharmacy&examCode=1870&etype=r18&type=intgrade,15-JAN-2025,bpharmacy,1870,r18,intgrade,,,R18,No,Regular,IV,I
RC/RV B.Tech III Year II Semester (R18) Supplementary Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1871&etype=r18&result=gradercrv&type=rcrvintgrade,20-MAR-2025,btech,1871,r18,rcrvintgrade,gradercrv,,R18,Yes,Supplementary,III,II
M.Tech II Year I Semester (R19) Regular Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=mtech&examCode=1872&etype=r19&type=intgrade,10-MAY-2025,mtech,1872,r19,intgrade,,,R19,No,Regular,II,I"""
        
        with open(CSV_FILE, 'w') as f:
            f.write(sample_data)
    
    # Load CSV data
    df = pd.read_csv(CSV_FILE)
    app.config['RESULTS_DF'] = df
    
    print(f"✅ Loaded {len(df)} results from CSV")
    
except Exception as e:
    print(f"❌ Error loading CSV: {e}")
    # Create empty DataFrame with expected columns
    columns = ['Title', 'URL', 'Exam_Date', 'degree', 'examCode', 'etype', 'type', 
               'result', 'grad', 'Regulation', 'Is_Supplementary', 'Exam_Type', 'Year', 'Semester']
    app.config['RESULTS_DF'] = pd.DataFrame(columns=columns)

def get_unique_values(column):
    """Get unique values for a column, handling NaN values"""
    df = app.config['RESULTS_DF']
    if column not in df.columns:
        return []
    
    # Handle NaN values and convert to strings
    values = df[column].dropna().astype(str).unique()
    # Filter out 'Unknown' and 'nan'
    return [v for v in values if v.lower() not in ['unknown', 'nan']]

def filter_results(filters):
    """Filter results based on provided criteria"""
    df = app.config['RESULTS_DF'].copy()
    
    # Apply filters
    if 'degree_type' in filters and filters['degree_type']:
        if filters['degree_type'] == 'BTech':
            df = df[df['degree'].str.lower().isin(['btech', 'b.e'])]
        elif filters['degree_type'] == 'B.Pharmacy':
            df = df[df['degree'].str.lower() == 'bpharmacy']
        elif filters['degree_type'] == 'MTech':
            df = df[df['degree'].str.lower() == 'mtech']
        elif filters['degree_type'] == 'M.Pharmacy':
            df = df[df['degree'].str.lower() == 'mpharmacy']
    
    if 'year' in filters and filters['year']:
        df = df[df['Year'].str.lower() == filters['year'].lower()]
    
    if 'semester' in filters and filters['semester']:
        df = df[df['Semester'].str.lower() == filters['semester'].lower()]
    
    if 'regulation' in filters and filters['regulation']:
        df = df[df['Regulation'].str.lower() == filters['regulation'].lower()]
    
    if 'exam_type' in filters and filters['exam_type']:
        if filters['exam_type'] == 'Regular':
            df = df[df['Exam_Type'].str.lower() == 'regular']
        elif filters['exam_type'] == 'Supplementary':
            df = df[df['Exam_Type'].str.contains('supplementary', case=False, na=False)]
    
    if 'rc_rv' in filters and filters['rc_rv']:
        if filters['rc_rv'] == 'Yes':
            df = df[df['Title'].str.contains('RC/RV|RCRV', case=False, na=False)]
    
    return df

@app.route('/api/mcp/context', methods=['GET'])
def get_mcp_context():
    """Get the MCP context for the AI chat interface"""
    return jsonify({
        "title": "JNTUH Results Assistant",
        "description": "Helps students find and download their results from JNTUH",
        "actions": [
            {
                "name": "search_results",
                "description": "Search for available results based on filters",
                "parameters": [
                    {"name": "degree_type", "type": "string", "required": True, "options": ["BTech", "B.Pharmacy", "MTech", "M.Pharmacy"]},
                    {"name": "year", "type": "string", "required": False},
                    {"name": "semester", "type": "string", "required": False},
                    {"name": "regulation", "type": "string", "required": False},
                    {"name": "exam_type", "type": "string", "required": False, "options": ["Regular", "Supplementary"]},
                    {"name": "rc_rv", "type": "string", "required": False, "options": ["Yes", "No"]}
                ]
            },
            {
                "name": "generate_result",
                "description": "Generate a PDF result for a specific roll number",
                "parameters": [
                    {"name": "examCode", "type": "string", "required": True},
                    {"name": "htno", "type": "string", "required": True}
                ]
            }
        ],
        "state": {
            "current_step": "initial",
            "available_filters": {
                "degree_types": ["BTech", "B.Pharmacy", "MTech", "M.Pharmacy"],
                "years": get_unique_values('Year'),
                "semesters": get_unique_values('Semester'),
                "regulations": get_unique_values('Regulation'),
                "exam_types": ["Regular", "Supplementary"],
                "rc_rv_options": ["Yes", "No"]
            }
        }
    })

@app.route('/api/mcp/action/search_results', methods=['POST'])
def mcp_search_results():
    """MCP action to search results based on filters"""
    try:
        filters = request.json
        
        # Filter results
        filtered_df = filter_results(filters)
        
        # Convert to list of dicts
        results = filtered_df.to_dict('records')
        
        # Prepare response for MCP
        response = {
            "status": "success",
            "data": {
                "count": len(results),
                "results": [{
                    "id": idx,
                    "title": result['Title'],
                    "exam_date": result['Exam_Date'],
                    "regulation": result['Regulation'],
                    "year": result['Year'],
                    "semester": result['Semester'],
                    "exam_type": result['Exam_Type'],
                    "exam_code": result['examCode'],
                    "is_rc_rv": "Yes" if "RC/RV" in result['Title'] or "RCRV" in result['Title'] else "No"
                } for idx, result in enumerate(results)]
            },
            "next_action": "select_result"
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/mcp/action/generate_result', methods=['POST'])
def mcp_generate_result():
    """MCP action to generate PDF result for a student"""
    try:
        data = request.json
        exam_code = data.get('examCode')
        htno = data.get('htno')
        
        if not exam_code or not htno:
            return jsonify({
                "status": "error",
                "message": "examCode and htno are required"
            }), 400
        
        # Find the result configuration
        df = app.config['RESULTS_DF']
        result_row = df[df['examCode'].astype(str) == str(exam_code)]
        
        if result_row.empty:
            return jsonify({
                "status": "error",
                "message": "Invalid exam code"
            }), 404
        
        # Extract parameters from the URL
        url = result_row.iloc[0]['URL']
        params = {}
        
        if '?' in url:
            query_string = url.split('?')[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
        
        # Add the roll number
        params['htno'] = htno
        
        # Call the JNTUH result action
        result_url = "http://results.jntuh.ac.in/resultAction"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': url,
            'Origin': 'http://results.jntuh.ac.in'
        }
        
        response = requests.post(result_url, data=params, headers=headers)
        response.raise_for_status()
        
        if "No Records Found" in response.text or "Invalid Hall Ticket Number" in response.text:
            return jsonify({
                "status": "error",
                "message": "No records found for this roll number"
            }), 404
        
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"result_{htno}_{exam_code}_{timestamp}.pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_filename)
        
        # Convert HTML to PDF
        HTML(string=response.text).write_pdf(pdf_path)
        
        # Return the PDF URL
        pdf_url = f"/static/pdfs/{pdf_filename}"
        
        return jsonify({
            "status": "success",
            "data": {
                "pdf_url": pdf_url,
                "filename": pdf_filename,
                "size": os.path.getsize(pdf_path),
                "message": "Result PDF generated successfully"
            },
            "next_action": "download_pdf"
        })
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch results: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/static/pdfs/<filename>')
def serve_pdf(filename):
    """Serve a generated PDF file"""
    pdf_path = os.path.join(PDF_DIR, filename)
    
    if not os.path.exists(pdf_path):
        abort(404)
    
    return send_file(
        pdf_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'results_count': len(app.config['RESULTS_DF']),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("="*60)
    print("JNTUH Results MCP Server")
    print("="*60)
    print(" • MCP Context Endpoint: /api/mcp/context")
    print(" • Search Results: /api/mcp/action/search_results (POST)")
    print(" • Generate Result: /api/mcp/action/generate_result (POST)")
    print(" • PDF Files: /static/pdfs/<filename>")
    print(" • Health Check: /api/health")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=True)