# Resume Parser

## 1. Summary

Resume Parser is a Python application that extracts structured information from PDF and DOCX resumes using a configurable Large Language Model (LLM) provider.

The application provides a FastAPI backend for resume processing and retrieval, along with a Streamlit web interface for uploading resumes and viewing extracted information.

### Features

- Upload PDF and DOCX resumes.
- Extract text using `pypdf` and `python-docx`.
- Use a configurable LLM provider for structured information extraction.
- Extract contact information, professional summary, work experience, education, skills, and certifications.
- Validate extracted information using Pydantic.
- Provide REST API endpoints using FastAPI.
- Protect API endpoints with Bearer token authentication.
- Save uploaded resume files to `data/uploads/`.
- Retrieve parsed resume data using a unique document ID while the backend is running.
- Display extracted information through a Streamlit interface.
- Upload and parse multiple resumes concurrently.
- Retry transient LLM connection, timeout, rate-limit, and server errors up to three times.

## 2. Prerequisites

Ensure the following are installed:

- Python 3.10 or newer
- pip
- An API key for the configured LLM provider

Check your Python installation:

```bash
python --version
pip --version
```

## 3. Project Setup

### Step 1: Create a virtual environment

Run this command from the project root directory:

```bash
python -m venv venv
```

### Step 2: Activate the virtual environment

**Windows — Command Prompt**

```bat
venv\Scripts\activate.bat
```

**Windows — PowerShell**

```powershell
.\venv\Scripts\Activate.ps1
```

**Linux/macOS**

```bash
source venv/bin/activate
```

### Step 3: Install dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

## 4. Environment Configuration

Create a `.env` file in the project root:

```env
API_BEARER_TOKEN=your_secret_api_token
API_BASE_URL=http://127.0.0.1:8000
```

Replace the placeholder values with your actual credentials.

- Set `LLM_PROVIDER` and the matching API key/model variables for your chosen provider; see `.env.example`.
- `API_BEARER_TOKEN`: Used to authenticate API requests.
- `API_BASE_URL`: The FastAPI backend URL used by Streamlit.

Never commit `.env` to version control. Add `.env` and `venv/` to `.gitignore`.

## 5. Start the FastAPI Server

Activate your virtual environment and run:

```bash
uvicorn app.main:app --reload
```

The backend will be available at:

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs
- ReDoc documentation: http://127.0.0.1:8000/redoc

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload and parse a resume |
| GET | `/api/resume/{document_id}` | Retrieve parsed resume data by document ID |

Both endpoints require a valid Bearer token.

Example authorization header:

```http
Authorization: Bearer your_secret_api_token
```

The upload endpoint returns a unique document ID and the extracted resume information. The GET endpoint retrieves the parsed data associated with that ID.

## 6. Start the Streamlit Application

Keep FastAPI running in the first terminal.

Open a second terminal, activate the same virtual environment, and run:

```bash
streamlit run ui/streamlit_app.py
```

Open the local URL shown in the terminal, typically:

http://localhost:8501

### Using the Application

1. Enter your API Bearer token in the sidebar.
2. Select one or more PDF or DOCX resumes.
3. Click **Extract Resumes** to parse up to four files concurrently.
4. Choose a parsed resume from the results selector to view its information and document ID.
5. Use **Retrieve Existing Resume** to retrieve parsed data by document ID.

## 7. Project Structure

```text
resume-parser/
│
├── app/
│   ├── main.py
│   ├── models.py
│   └── services/
│       ├── parser.py
│       ├── prompts.py
│       └── llm_service.py
│
├── ui/
│   └── streamlit_app.py
│
├── data/
│   └── uploads/
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

### File Descriptions

- `app/main.py`: Defines API endpoints, authentication, and request handling.
- `app/models.py`: Defines Pydantic schemas for resume data and API responses.
- `app/services/parser.py`: Extracts text from PDF/DOCX files and coordinates resume parsing.
- `app/services/prompts.py`: Contains the LLM extraction prompt.
- `app/services/llm_service.py`: Communicates with the configured LLM provider.
- `ui/streamlit_app.py`: Provides the web interface.
- `data/uploads/`: Stores uploaded resume files.
- `.env`: Stores environment variables.
- `.env.example`: Documents the required environment variables.
- `requirements.txt`: Lists Python dependencies.

The upload directory is created automatically by the application when its initialization code runs.

## 8. Storage and Persistence

Uploaded resume files are saved to `data/uploads/` using unique filenames.

Parsed resume results are currently stored in an in-memory Python dictionary. This allows the GET endpoint to retrieve previously parsed data while the FastAPI process is running.

**Important limitation:** When the FastAPI server stops or restarts, the in-memory parsed results are lost. For persistent retrieval across restarts or multiple server instances, the dictionary can be replaced with a database-backed storage layer (for example, PostgreSQL).

Uploaded resume files are stored on the server's local disk in `data/uploads/`. They do not accumulate in RAM, but they use disk space and will grow over time unless files are deleted. For a deployed or multi-instance application, cloud object storage (such as Amazon S3, Google Cloud Storage, or Azure Blob Storage) is a better fit; keep file metadata and storage keys in the database rather than relying on a local path.

## 9. Error Handling

The API and Streamlit interface handle common user-facing errors, including:

- Unsupported file formats and empty uploads.
- Invalid files or documents without readable text (scanned PDFs may need OCR).
- Missing or invalid Bearer tokens.
- Resume content that cannot be parsed or validated.
- Temporary parsing-service failures, request timeouts, and an unavailable API server.
- Unknown document IDs.
- Unexpected processing failures, without exposing internal exception details in the UI.

The API returns appropriate HTTP status codes and safe messages for these cases. Technical exception details are kept in server logs rather than displayed to users.

Resume parsing uses asynchronous LLM requests, while PDF/DOCX extraction runs off the API event loop. The Streamlit uploader submits up to four selected resumes concurrently. Transient LLM provider failures are retried up to three total attempts with a short backoff; invalid files, unreadable content, invalid LLM output, and other non-transient errors are not retried.

## 10. Important Notes

- A valid API key for the selected LLM provider is required to parse new resumes.
- Processing time depends on the LLM provider, model, and resume length.
- Scanned PDFs may require OCR because ordinary PDF text extraction may not detect text in images.
- Uploaded resumes contain personal information. Restrict access to stored files and define a retention/deletion policy.
