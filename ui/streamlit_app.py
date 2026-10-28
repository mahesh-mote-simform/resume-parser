
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Resume Parser", page_icon="📄", layout="wide")

API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.getenv("API_BEARER_TOKEN", "")

# Keep results when Streamlit reruns
if "page" not in st.session_state:
    st.session_state.page = "Upload Resume"

if "resumes" not in st.session_state:
    st.session_state.resumes = []

st.title("📄 Resume Parser")

# Sidebar navigation
with st.sidebar:
    st.header("Navigation")

    if st.button("📤 Upload Resume", use_container_width=True):
        st.session_state.page = "Upload Resume"

    if st.button("🔎 Retrieve Existing Resume", use_container_width=True):
        st.session_state.page = "Retrieve Existing Resume"

    st.divider()
    st.write("API Settings")
    token = st.text_input("Bearer Token", value=TOKEN, type="password")

headers = {"Authorization": f"Bearer {token}"}


def parse_api_response(response: requests.Response) -> dict | None:
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        st.error("The resume service returned an unexpected response. Please try again later.")
        return None

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        st.error("The resume service returned an unexpected response. Please try again later.")
        return None

    return payload


def show_api_error(status_code: int) -> None:
    """Display a user-safe message for a failed API request."""
    messages = {
        400: "This file is unsupported or empty. Please upload a non-empty PDF or DOCX resume.",
        401: "Authentication failed. Please check the API token and try again.",
        404: "Resume not found. Please check the document ID and try again.",
        422: "We couldn't read or parse this resume. Please upload a readable PDF or DOCX and try again.",
        502: "The resume parsing service is temporarily unavailable. Please try again later.",
        503: "The resume parsing service is temporarily unavailable. Please try again later.",
    }
    st.error(messages.get(status_code, "The request couldn't be completed. Please try again later."))


def show_connection_error(error: requests.RequestException) -> None:
    if isinstance(error, requests.Timeout):
        st.error("The resume service took too long to respond. Please try again.")
    elif isinstance(error, requests.ConnectionError):
        st.error("The resume service is unavailable. Please try again later.")
    else:
        st.error("The request couldn't be completed. Please try again later.")


# Upload page
if st.session_state.page == "Upload Resume":
    st.header("Upload Resume")

    files = st.file_uploader(
        "Choose PDF or DOCX files",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )

    if st.button("Extract Resumes", disabled=not files or not token):
        st.session_state.resumes = []
        parsed_resumes = []
        uploads = [
            (file.name, file.getvalue(), file.type)
            for file in files
        ]

        with st.spinner(f"Extracting {len(uploads)} resume(s)..."):
            with ThreadPoolExecutor(max_workers=min(len(uploads), 4)) as executor:
                futures = {
                    executor.submit(
                        requests.post,
                        f"{API_URL}/api/upload",
                        headers=headers,
                        files={"file": (name, content, content_type)},
                        timeout=120,
                    ): name
                    for name, content, content_type in uploads
                }

                for future in as_completed(futures):
                    filename = futures[future]
                    try:
                        response = future.result()
                    except requests.RequestException as error:
                        st.error(f"{filename}:")
                        show_connection_error(error)
                        continue

                    if not response.ok:
                        st.error(f"{filename}:")
                        show_api_error(response.status_code)
                        continue

                    result = parse_api_response(response)
                    if result is not None:
                        parsed_resumes.append(result)
                        st.success(f"{filename}: resume parsed successfully.")

        st.session_state.resumes = parsed_resumes

# Retrieve page
else:
    st.header("Retrieve Existing Resume")

    document_id = st.text_input("Enter Document ID")

    if st.button("Retrieve Resume", disabled=not document_id.strip() or not token):
        try:
            with st.spinner("Retrieving resume..."):
                response = requests.get(
                    f"{API_URL}/api/resume/{document_id.strip()}",
                    headers=headers,
                    timeout=30,
                )

            if response.ok:
                result = parse_api_response(response)
                if result is not None:
                    st.session_state.resumes = [result]
                    st.success("Resume retrieved successfully!")
            else:
                show_api_error(response.status_code)

        except requests.RequestException as error:
            show_connection_error(error)

# Display the extracted resume
if st.session_state.resumes:
    selected_index = st.selectbox(
        "Select a parsed resume",
        range(len(st.session_state.resumes)),
        format_func=lambda index: (
            st.session_state.resumes[index].get("filename")
            or st.session_state.resumes[index].get("document_id", "Resume")
        ),
    )
    result = st.session_state.resumes[selected_index]
    data = result.get("data", {})
    contact = data.get("contact_info", {})

    st.divider()
    st.header("Extracted Resume Details")

    st.caption(f"Document ID: {result.get('document_id', 'N/A')}")

    st.subheader("Contact Information")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Name:**", contact.get("name") or "Not provided")
        st.write("**Email:**", contact.get("email") or "Not provided")

    with col2:
        st.write("**Phone:**", contact.get("phone") or "Not provided")
        st.write("**Location:**", contact.get("location") or "Not provided")

    st.subheader("Professional Summary")
    st.write(data.get("professional_summary") or "Not provided")

    st.subheader("Work Experience")
    for job in data.get("work_experience", []):
        with st.expander(
            f"{job.get('job_title') or 'Position'} - "
            f"{job.get('company') or 'Company'}"
        ):
            st.write("**Duration:**", job.get("duration") or "Not provided")
            st.write("**Start Date:**", job.get("start_date") or "Not provided")
            st.write("**End Date:**", job.get("end_date") or "Not provided")

            for responsibility in job.get("responsibilities", []):
                st.markdown(f"- {responsibility}")

    st.subheader("Education")
    for education in data.get("education", []):
        st.write("**Degree:**", education.get("degree") or "Not provided")
        st.write("**Institution:**", education.get("institution") or "Not provided")
        st.write("**Field:**", education.get("field_of_study") or "Not provided")
        st.write("**Graduation Year:**", education.get("graduation_year") or "Not provided")

    st.subheader("Skills")
    skills = data.get("skills", {})

    st.write("**Technical Skills:**", ", ".join(skills.get("technical", [])) or "None")
    st.write("**Soft Skills:**", ", ".join(skills.get("soft", [])) or "None")

    st.subheader("Certifications")
    for certification in data.get("certifications", []):
        st.write("**Name:**", certification.get("name") or "Not provided")
        st.write("**Issuer:**", certification.get("issuing_organization") or "Not provided")
        st.write("**Year:**", certification.get("issue_year") or "Not provided")

    with st.expander("View Raw JSON"):
        st.json(result)
