
from pydantic import BaseModel, Field


# ---------- Resume data ----------

class ContactInfo(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None


class WorkExperience(BaseModel):
    company: str | None = None
    job_title: str | None = None
    duration: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    responsibilities: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str | None = None
    institution: str | None = None
    field_of_study: str | None = None
    graduation_year: str | None = None


class Skills(BaseModel):
    technical: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    name: str | None = None
    issuing_organization: str | None = None
    issue_year: str | None = None


class ResumeData(BaseModel):
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    professional_summary: str | None = None
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    certifications: list[Certification] = Field(default_factory=list)


# ---------- API 1: POST /api/upload ----------

class ResumeUploadResponse(BaseModel):
    document_id: str
    filename: str
    data: ResumeData


# ---------- API 2: GET /api/resume/{document_id} ----------

class ResumeResponse(BaseModel):
    document_id: str
    data: ResumeData


# ---------- Error response ----------

class ErrorResponse(BaseModel):
    detail: str
