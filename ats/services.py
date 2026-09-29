import io
import re
from collections import Counter

from docx import Document
from pypdf import PdfReader


STOP_WORDS = {
    "about", "after", "also", "and", "are", "but", "for", "from", "have",
    "into", "its", "more", "our", "that", "the", "their", "this", "will",
    "with", "you", "your", "work", "working", "years", "year", "role",
    "team", "job", "candidate", "required", "requirements", "responsibilities",
}
SECTION_TITLES = {
    "summary": {"summary", "professional summary", "profile", "objective"},
    "experience": {
        "experience", "work experience", "professional experience", "employment",
        "employment history", "work history", "professional background", "internship",
        "internships",
    },
    "education": {
        "education", "academic background", "qualifications", "academic qualifications",
        "coursework",
    },
    "skills": {"skills", "technical skills", "core competencies"},
    "projects": {"projects", "selected projects"},
    "certifications": {"certifications", "licenses", "licenses and certifications"},
}
EDUCATION_TERMS = {
    "bachelor", "bachelors", "bachelor's", "master", "masters", "master's",
    "degree", "diploma", "phd", "doctorate", "graduate", "postgraduate",
}


class ResumeTextError(ValueError):
    """Raised when an uploaded resume cannot be read as searchable text."""


def extract_resume_text(resume):
    extension = resume.file_extension()
    try:
        with resume.resume_file.open("rb") as resume_file:
            file_bytes = resume_file.read()
    except Exception as error:
        raise ResumeTextError("We could not read this resume. Upload a valid PDF or DOCX file.") from error
    return extract_resume_file_text(file_bytes, extension)


def extract_resume_upload_text(uploaded_file):
    extension = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    try:
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)
    except Exception as error:
        raise ResumeTextError("We could not read this resume. Upload a valid PDF or DOCX file.") from error
    return extract_resume_file_text(file_bytes, extension)


def extract_resume_file_text(file_bytes, extension):
    if extension not in {"pdf", "docx"}:
        raise ResumeTextError("ATS analysis supports searchable PDF and DOCX files. Legacy DOC files are not supported.")

    try:
        if extension == "pdf":
            reader = PdfReader(io.BytesIO(file_bytes), strict=False)
            if reader.is_encrypted:
                try:
                    if not reader.decrypt(""):
                        raise ResumeTextError("This PDF is password protected. Upload an unlocked copy to analyze it.")
                except NotImplementedError as error:
                    raise ResumeTextError("This PDF encryption is not supported. Upload an unlocked copy to analyze it.") from error
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            document = Document(io.BytesIO(file_bytes))
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            paragraphs.extend(
                cell.text
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            )
            text = "\n".join(paragraphs)
    except ResumeTextError:
        raise
    except Exception as error:
        raise ResumeTextError("We could not read this resume. Upload a valid PDF or DOCX file.") from error

    text = "\n".join(
        " ".join(line.split())
        for line in text.splitlines()
        if line.strip()
    ).strip()
    if len(text) < 30:
        raise ResumeTextError("No readable text was found. Scanned PDFs need OCR before they can be analyzed.")
    return text


def _contains_phrase(text, phrase):
    escaped = re.escape(phrase.strip())
    if not escaped:
        return False
    return re.search(r"(?<!\w)" + escaped + r"(?!\w)", text, re.IGNORECASE) is not None


def _section_titles_in(resume_text):
    return {
        category
        for line in resume_text.splitlines()
        for category, titles in SECTION_TITLES.items()
        if line.strip().casefold().rstrip(":") in titles
    }


def _job_skills(job):
    values = re.split(r"[,;\n]+", job.skills or "")
    unique = {}
    for value in values:
        cleaned = value.strip()
        if cleaned:
            unique.setdefault(cleaned.casefold(), cleaned)
    return list(unique.values())


def _job_keywords(job):
    job_text = " ".join(
        [job.title or "", job.skills or "", job.description or "", job.requirements or "", job.responsibilities or ""]
    ).lower()
    words = re.findall(r"[a-z][a-z0-9+#.-]{2,}", job_text)
    counts = Counter(word.strip(".-") for word in words)
    return [
        word
        for word, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if len(word.strip(".-")) > 2 and word.strip(".-") not in STOP_WORDS
    ][:30]


def analyze_resume_text(resume_text, job):
    normalized_resume = re.sub(r"\s+", " ", resume_text).casefold()
    required_skills = _job_skills(job)
    matched_skills = [skill for skill in required_skills if _contains_phrase(normalized_resume, skill)]
    missing_skills = [skill for skill in required_skills if skill not in matched_skills]

    job_keywords = _job_keywords(job)
    matched_keywords = [keyword for keyword in job_keywords if _contains_phrase(normalized_resume, keyword)]
    missing_keywords = [keyword for keyword in job_keywords if keyword not in matched_keywords]

    skills_score = round(40 * len(matched_skills) / len(required_skills)) if required_skills else 0
    keywords_score = round(20 * len(matched_keywords) / len(job_keywords)) if job_keywords else 0

    resume_sections = _section_titles_in(resume_text)
    has_experience_section = "experience" in resume_sections
    year_values = [float(value) for value in re.findall(r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", normalized_resume)]
    stated_years = max(year_values, default=0)
    experience_targets = {"entry": 0, "mid": 2, "senior": 5}
    target_years = experience_targets.get(job.experience_level, 0)
    experience_score = 8 if has_experience_section else 0
    if target_years == 0:
        experience_score += 17 if stated_years or has_experience_section else 0
    elif stated_years:
        experience_score += round(17 * min(stated_years / target_years, 1))

    has_education_section = "education" in resume_sections
    requested_education_terms = {
        term for term in EDUCATION_TERMS
        if _contains_phrase(job.requirements or "", term)
        or _contains_phrase(job.description or "", term)
    }
    matching_education_terms = [
        term for term in requested_education_terms if _contains_phrase(normalized_resume, term)
    ]
    if requested_education_terms:
        education_score = round(10 * len(matching_education_terms) / len(requested_education_terms))
    else:
        education_score = 10 if has_education_section else 0

    section_count = len(resume_sections)
    structure_score = 5 if section_count >= 3 else 3 if section_count == 2 else 1 if section_count == 1 else 0
    overall_score = min(
        100,
        skills_score + experience_score + keywords_score + education_score + structure_score,
    )

    suggestions = []
    if missing_skills:
        suggestions.append(f"Highlight relevant experience with: {', '.join(missing_skills[:3])}.")
    if missing_keywords:
        suggestions.append(f"Consider including relevant terms such as: {', '.join(missing_keywords[:3])}.")
    if not has_experience_section:
        suggestions.append("Add a clearly labeled experience section with role dates and duration.")
    if not has_education_section:
        suggestions.append("Add a clearly labeled education section.")
    if not suggestions:
        suggestions.append("Your resume includes evidence for the main requirements of this role.")

    return {
        "overall_score": overall_score,
        "skills_score": skills_score,
        "experience_score": experience_score,
        "keywords_score": keywords_score,
        "education_score": education_score,
        "structure_score": structure_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "suggestions": suggestions,
    }
