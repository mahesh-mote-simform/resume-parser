
import os
import secrets
import asyncio
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.models import  ResumeData, ResumeUploadResponse, ResumeResponse, ErrorResponse
from app.services.parser import (
    ResumeParseError,
    ResumeProcessingServiceError,
    ResumeReadError,
    get_parsed_resume,
    get_text,
)
from app.utils.logger import app_logger

load_dotenv()

app = FastAPI(title="Resume Parser API")

# Upload directory at the project root
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Temporary storage for parsed results
resumes: dict[str, ResumeData] = {}

security = HTTPBearer(auto_error=False)


def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    """Verify the Bearer token for protected endpoints."""

    expected_token = os.getenv("API_BEARER_TOKEN")

    if not expected_token:
        app_logger.error("API_BEARER_TOKEN is not configured")
        raise HTTPException( status_code=500, detail="API authentication is not configured.")

    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not secrets.compare_digest(
            credentials.credentials,
            expected_token,
        )
    ):
        app_logger.warning("Invalid or missing Bearer token attempted")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post(
    "/api/upload",
    response_model=ResumeUploadResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def upload_resume(
    file: UploadFile = File(...),
    _: None = Depends(verify_token),
):
    """Save and parse an uploaded PDF or DOCX resume."""

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in {".pdf", ".docx"}:
        raise HTTPException( status_code=400, detail="Only PDF and DOCX files are supported.")

    document_id = str(uuid4())
    saved_path = UPLOAD_DIR / f"{document_id}{extension}"

    try:
        # Save the original uploaded file
        content = await file.read()

        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        await asyncio.to_thread(saved_path.write_bytes, content)
        app_logger.info("Uploaded file saved: %s", saved_path.name)

        # Extract text from the saved file
        with saved_path.open("rb") as saved_file:
            resume_text = await asyncio.to_thread(get_text, saved_file, saved_path.name)

        # Parse the resume using the LLM
        parsed_data = await get_parsed_resume(resume_text)

        # Validate the LLM output
        resume_data = ResumeData.model_validate(parsed_data)

        # Store the parsed data
        resumes[document_id] = resume_data

        app_logger.info("Resume parsed successfully: %s", document_id)

        return ResumeUploadResponse(document_id=document_id, filename=file.filename, data=resume_data)

    except HTTPException:
        raise

    except ResumeReadError as exc:
        raise HTTPException(
            status_code=422,
            detail="This resume could not be read. Upload a valid PDF or DOCX with selectable text.",
        ) from exc

    except ResumeParseError as exc:
        raise HTTPException(
            status_code=422,
            detail="We couldn't parse this resume. Check that it contains readable resume information and try again.",
        ) from exc

    except ValidationError as exc:
        app_logger.exception("Parsed resume data did not match the expected schema")
        raise HTTPException(
            status_code=422,
            detail="We couldn't extract resume information. Please check the file and try again.",
        ) from exc

    except ResumeProcessingServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail="The resume parsing service is temporarily unavailable. Please try again later.",
        ) from exc

    except Exception as exc:
        app_logger.exception("Failed to process uploaded resume")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the resume. Please try again later.",
        ) from exc

    finally:
        await file.close()


@app.get(
    "/api/resume/{document_id}",
    response_model=ResumeResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_resume(
    document_id: str,
    _: None = Depends(verify_token),
):
    """Retrieve parsed resume data by document ID."""
    app_logger.info("Retrieving resume for document ID: %s", document_id)

    resume_data = resumes.get(document_id)

    if resume_data is None:
        app_logger.warning("Resume not found for document ID: %s", document_id)
        raise HTTPException(status_code=404, detail="Resume not found.")

    app_logger.info("Successfully retrieved resume for document ID: %s", document_id)
    return ResumeResponse(document_id=document_id, data=resume_data)
