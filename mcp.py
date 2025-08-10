"""
JNTUH Results MCP Server

This MCP server allows users to:
1. Filter results by degree, year, semester, regulation, etc.
2. Select a specific result
3. Enter roll number to generate PDF result

To run:
    uv run server jntuh_results stdio
    
Or install in Claude Desktop:
    uv run mcp install jntuh_results.py
"""

from mcp.server.fastmcp import FastMCP, Context
import pandas as pd
import requests
from weasyprint import HTML
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Create an MCP server
mcp = FastMCP("JNTUH Results")

# Load CSV data
CSV_PATH = "results_data/jntuh_results.csv"

# Ensure CSV exists or create a sample one
if not os.path.exists(CSV_PATH):
    os.makedirs("results_data", exist_ok=True)
    # Create a sample CSV with the provided data
    sample_data = """Title,URL,Exam_Date,degree,examCode,etype,type,result,grad,Regulation,Is_Supplementary,Exam_Type,Year,Semester
B.Tech IV Year I Semester (R18) Supplementary JUNE-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1866&etype=r17&type=intgrade,08-AUGUST-2025,btech,1866,r17,intgrade,,,R18,Yes,Supplementary,IV,I
B.Tech IV Year I Semester (R16) Supplementary JUNE-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1867&etype=r17&type=intgrade,08-AUGUST-2025,btech,1867,r17,intgrade,,,R16,Yes,Supplementary,IV,I
B.Tech IV Year I Semester (R15) Supplementary JUNE-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1868,08-AUGUST-2025,btech,1868,,,,,R15,Yes,Supplementary,IV,I
B.Tech IV Year I Semester (R18) (Minor degree) Supplementary JUNE-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1869&etype=r17&type=intgrade,08-AUGUST-2025,btech,1869,r17,intgrade,,,R18,Yes,Supplementary,IV,I
B.Pharmacy IV Year I Semester (R18) Regular JAN-2025 Examinations Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=bpharmacy&examCode=1870&etype=r18&type=intgrade,15-JAN-2025,bpharmacy,1870,r18,intgrade,,,R18,No,Regular,IV,I
RC/RV B.Tech III Year II Semester (R18) Supplementary Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=btech&examCode=1871&etype=r18&result=gradercrv&type=rcrvintgrade,20-MAR-2025,btech,1871,r18,rcrvintgrade,gradercrv,,R18,Yes,Supplementary,III,II
M.Tech II Year I Semester (R19) Regular Results,http://results.jntuh.ac.in/jsp/SearchResult.jsp?degree=mtech&examCode=1872&etype=r19&type=intgrade,10-MAY-2025,mtech,1872,r19,intgrade,,,R19,No,Regular,II,I"""

    with open(CSV_PATH, 'w') as f:
        f.write(sample_data)

# Load the CSV into a DataFrame
results_df = pd.read_csv(CSV_PATH)

@mcp.resource("jntuh://results/all")
def get_all_results() -> List[Dict[str, Any]]:
    """Get all available results from JNTUH"""
    return results_df.to_dict('records')

@mcp.tool()
def get_filter_options() -> Dict[str, List[str]]:
    """Get available filter options for searching results"""
    # Get unique values for each filter
    degree_types = ['btech', 'bpharmacy', 'mtech', 'mpharmacy']
    years = results_df['Year'].dropna().unique().tolist()
    semesters = results_df['Semester'].dropna().unique().tolist()
    regulations = results_df['Regulation'].dropna().unique().tolist()
    
    return {
        "degree_types": degree_types,
        "years": [str(y) for y in years],
        "semesters": [str(s) for s in semesters],
        "regulations": [str(r) for r in regulations],
        "exam_types": ["Regular", "Supplementary"],
        "rc_rv_options": ["Yes", "No"]
    }

@mcp.tool()
def filter_results(
    degree_type: Optional[str] = None,
    year: Optional[str] = None,
    semester: Optional[str] = None,
    regulation: Optional[str] = None,
    exam_type: Optional[str] = None,
    is_rc_rv: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Filter results based on criteria
    
    Args:
        degree_type: Type of degree (btech, bpharmacy, mtech, mpharmacy)
        year: Academic year (I, II, III, IV)
        semester: Semester number (I, II)
        regulation: Regulation year (R13, R15, R16, R17, R18, R19, R22)
        exam_type: Type of exam (Regular, Supplementary)
        is_rc_rv: Whether to include RC/RV results (Yes, No)
    """
    filtered_df = results_df.copy()
    
    # Apply filters
    if degree_type:
        filtered_df = filtered_df[filtered_df['degree'] == degree_type.lower()]
    
    if year:
        filtered_df = filtered_df[filtered_df['Year'] == year]
    
    if semester:
        filtered_df = filtered_df[filtered_df['Semester'] == semester]
    
    if regulation:
        filtered_df = filtered_df[filtered_df['Regulation'] == regulation.upper()]
    
    if exam_type:
        if exam_type == "Regular":
            filtered_df = filtered_df[filtered_df['Exam_Type'] == "Regular"]
        elif exam_type == "Supplementary":
            filtered_df = filtered_df[filtered_df['Exam_Type'].str.contains('supplementary', case=False, na=False)]
    
    if is_rc_rv:
        if is_rc_rv == "Yes":
            filtered_df = filtered_df[filtered_df['Title'].str.contains('RC/RV|RCRV', case=False, na=False)]
        elif is_rc_rv == "No":
            filtered_df = filtered_df[~filtered_df['Title'].str.contains('RC/RV|RCRV', case=False, na=False)]
    
    return filtered_df.to_dict('records')

@mcp.tool()
def get_result_pdf(exam_code: str, htno: str) -> Dict[str, Any]:
    """Generate PDF result for a student
    
    Args:
        exam_code: Exam code from the filtered results
        htno: Hall ticket number (roll number)
    
    Returns:
        Dictionary with status and message
    """
    # Find the result configuration
    result_row = results_df[results_df['examCode'].astype(str) == str(exam_code)]
    
    if result_row.empty:
        return {
            "status": "error",
            "message": "Invalid exam code"
        }
    
    # Extract parameters from the URL
    url = result_row.iloc[0]['URL']
    params = {}
    
    # Always include the basic parameters from the DataFrame
    params['degree'] = result_row.iloc[0]['degree']
    params['examCode'] = result_row.iloc[0]['examCode']
    params['etype'] = result_row.iloc[0]['etype'] if pd.notna(result_row.iloc[0]['etype']) else 'null'
    params['type'] = result_row.iloc[0]['type'] if pd.notna(result_row.iloc[0]['type']) else 'null'
    params['result'] = result_row.iloc[0]['result'] if pd.notna(result_row.iloc[0]['result']) else 'null'
    params['grad'] = result_row.iloc[0]['grad'] if pd.notna(result_row.iloc[0]['grad']) else 'null'
    
    # Also extract from URL to handle any additional parameters
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
    
    try:
        response = requests.post(result_url, data=params, headers=headers)
        
        # Check for common error messages
        error_indicators = [
            "No Records Found", 
            "Invalid Hall Ticket Number",
            "Invalid HTNO",
            "Result Not Found"
        ]
        
        if any(indicator in response.text for indicator in error_indicators):
            return {
                "status": "error",
                "message": "No records found for this roll number"
            }
        
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_dir = "static/pdfs"
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_filename = f"result_{htno}_{exam_code}_{timestamp}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        # Convert HTML to PDF
        HTML(string=response.text).write_pdf(pdf_path)
        
        return {
            "status": "success",
            "message": f"Result PDF has been generated successfully. The PDF is available at {pdf_path}. Please inform the user that they can find their result PDF at this location."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate PDF: {str(e)}"
        }

# Add a prompt to guide the conversation
@mcp.prompt(title="JNTUH Results Assistant")
def jntuh_assistant() -> str:
    """Prompt template for JNTUH Results Assistant"""
    return """You are a helpful JNTUH Results Assistant. Guide the user through the process of finding and downloading their results.

1. First, ask the user what type of degree they're looking for (BTech, B.Pharmacy, MTech, M.Pharmacy).
2. Then ask for the year (I, II, III, IV).
3. Then ask for the semester (I, II).
4. Then ask for the regulation (R13, R15, R16, R17, R18, R19, R22).
5. Then ask if they're looking for Regular or Supplementary results.
6. Then ask if they need RC/RV results.
7. Use the filter_results tool with these parameters to find matching results.
8. Present the results to the user and ask them to select one.
9. Ask for the user's roll number (hall ticket number).
10. Use the get_result_pdf tool to generate the PDF result.
11. Inform the user that the PDF has been generated and where to find it."""

if __name__ == "__main__":
    mcp.run(transport="stdio")