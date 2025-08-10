# 📄 JNTUH Results MCP Server

A **Flask** + **FastMCP** server that helps students **search, filter, and download JNTUH results** as PDFs.  
It supports both a **REST API** for web clients and an **MCP (Model Context Protocol)** interface for AI assistants like Claude Desktop.

## ✨ Features

- **Search results** by:
  - Degree type (BTech, B.Pharmacy, MTech, M.Pharmacy)
  - Year, Semester, Regulation
  - Exam Type (Regular / Supplementary)
  - RC/RV results filter
- **Generate result PDF** for any hall ticket number (HTNO)
- **Download results** in PDF format directly from the server
- **Sample CSV data** provided if none exists
- **MCP support** to integrate into Claude Desktop or other MCP-enabled clients
- **CORS enabled** for easy frontend integration

## 📂 Project Structure

```
project/
├── results_data/            # Results dataset directory (auto-created)
│   └── jntuh_results.csv   # Auto-generated sample data if not exists
├── static/
│   └── pdfs/               # Generated result PDFs (auto-created)
├── app.py                  # Flask REST API server
├── mcp.py                  # MCP server implementation
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .gitattributes         # Git attributes
└── .gitignore             # Git ignore rules
```

## ⚙️ Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/yourusername/jntuh-results-mcp.git
cd jntuh-results-mcp
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- Flask
- Flask-CORS
- pandas
- requests
- weasyprint
- mcp (specifically `mcp.server.fastmcp`)

## 🚀 Running the Server

### Option 1 — Run as REST API

```bash
python app.py
```

By default, it runs on:
```
http://0.0.0.0:5000
```

**Available Endpoints:**
- Health check: `GET /api/health`
- Get MCP context: `GET /api/mcp/context`
- Search results: `POST /api/mcp/action/search_results`
- Generate PDF: `POST /api/mcp/action/generate_result`
- Download PDF: `GET /static/pdfs/<filename>`

### Option 2 — Run as MCP Server

```bash
python mcp.py
```

**Note:** The MCP server runs with `transport="stdio"` and is designed to be used with MCP-compatible clients like Claude Desktop.

## 🤖 MCP Integration

### Claude Desktop Configuration

Add to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "jntuh-results": {
      "command": "python",
      "args": ["path/to/mcp.py"]
    }
  }
}
```

### MCP Prompt Flow

When used with Claude Desktop or any MCP-compatible AI assistant:

1. Ask user for degree type
2. Ask for year → semester → regulation  
3. Ask for exam type → RC/RV filter
4. Use `filter_results` tool to get matching results
5. Ask for hall ticket number
6. Use `get_result_pdf` tool to generate and share the PDF

## 📊 API Usage Examples

### Search Results

```bash
curl -X POST http://localhost:5000/api/mcp/action/search_results \
  -H "Content-Type: application/json" \
  -d '{
    "degree_type": "BTech",
    "year": "IV",
    "semester": "I",
    "regulation": "R18",
    "exam_type": "Supplementary",
    "rc_rv": "No"
  }'
```

### Generate Result PDF

```bash
curl -X POST http://localhost:5000/api/mcp/action/generate_result \
  -H "Content-Type: application/json" \
  -d '{
    "examCode": "1866",
    "htno": "18A81A0501"
  }'
```

## 🛠️ Development

### Running in Development Mode

```bash
export FLASK_ENV=development
python app.py
```

### Testing MCP Tools

```bash
# Test the MCP server
python mcp.py
```

### Available MCP Tools

- `get_filter_options()`: Get available filter options for searching results
- `filter_results()`: Filter results based on criteria (degree_type, year, semester, regulation, exam_type, is_rc_rv)
- `get_result_pdf()`: Generate PDF result for a student using exam_code and htno

### Available MCP Resources

- `jntuh://results/all`: Get all available results from the CSV data

## 📝 Notes

- **Auto-generated sample data**: The project automatically creates a sample `jntuh_results.csv` file if it doesn't exist with 7 sample records
- **Directory creation**: Both `results_data/` and `static/pdfs/` directories are created automatically by the applications
- **PDF storage**: Generated PDFs are saved in `static/pdfs/` with timestamp-based filenames: `result_{htno}_{exam_code}_{timestamp}.pdf`
- **Dual server architecture**: Flask REST API for web clients, FastMCP server for AI assistants
- **Error handling**: Both servers include comprehensive error handling for invalid hall ticket numbers and exam codes
- The JNTUH result system may block requests if abused. Keep traffic reasonable
- Ensure you have appropriate permissions and follow JNTUH's terms of service

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This tool is for educational purposes. Please respect JNTUH's servers and terms of service. The authors are not responsible for any misuse of this software.

## 📞 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Contact: harshrb2424@gmail.com

---

Made with ❤️ for JNTUH students
