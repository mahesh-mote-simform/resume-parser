
import asyncio
import logging
from pathlib import Path
from io import BytesIO

from docx import Document
from pypdf import PdfReader

from app.services.llm_service import get_llm
from app.services.prompt import RESUME_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class ResumeReadError(Exception):
    """Raised when an uploaded file cannot be read as a resume."""


class ResumeParseError(Exception):
    """Raised when the resume content cannot be parsed into structured data."""


class ResumeProcessingServiceError(Exception):
    """Raised when the configured resume parsing service fails."""


def read_pdf(file):
    """Read text from a PDF file."""
    logger.debug("Reading PDF file")
    pdf = PdfReader(file)
    text = ""

    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text

    logger.info(f"Extracted {len(text)} characters from PDF")
    return text.strip()


def read_docx(file):
    """Read text from a DOCX file."""
    logger.debug("Reading DOCX file")
    document = Document(BytesIO(file.read()))

    text = ""
    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"

    logger.info(f"Extracted {len(text)} characters from DOCX")
    return text.strip()


def get_text(file, filename):
    """Extract text from an uploaded PDF or DOCX file."""
    logger.info(f"Extracting text from file: {filename}")
    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".docx"}:
        logger.warning(f"Unsupported file extension: {extension}")
        raise ValueError("Only PDF and DOCX files are supported.")

    try:
        file.seek(0)

        if extension == ".pdf":
            text = read_pdf(file)
        else:
            text = read_docx(file)

        if not text:
            logger.warning(f"No readable text found in file: {filename}")
            raise ResumeReadError

        logger.info(f"Successfully extracted {len(text)} characters from {filename}")
        return text

    except ResumeReadError:
        raise
    except Exception as e:
        logger.exception(f"Failed to read uploaded resume: {filename}")
        raise ResumeReadError from e


async def get_parsed_resume(resume_text: str) -> dict:
    """Extract structured resume information using an LLM."""
    logger.info(f"Starting LLM parsing for resume ({len(resume_text)} chars)")
    try:
        result = await get_llm(
            prompt=RESUME_EXTRACTION_PROMPT,
            resume_context=resume_text,
        )
        logger.info(f"LLM parsing completed successfully ({len(str(result))} chars)")
        return result
    except ValueError as e:
        logger.warning("Resume parsing returned an invalid response")
        raise ResumeParseError from e
    except Exception as e:
        logger.exception("Resume parsing service failed")
        raise ResumeProcessingServiceError from e
