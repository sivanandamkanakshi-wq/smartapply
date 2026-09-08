"""
Real ATS scoring for SmartApply — reads the actual uploaded resume PDF
instead of just checking profile completeness.

SETUP:
1. Install the PDF text extraction library:
       pip install pypdf
   (add "pypdf" to requirements.txt too)

2. Save this file as features/resume_ats.py

3. In app.py, add near your other imports:
       from features.resume_ats import calculate_ats_score

4. In the resume_manager() route's GET section, compute the score from
   the actual saved file (see instructions after this file).
"""

import re
from pypdf import PdfReader

SECTION_KEYWORDS = [
    "experience", "education", "skills", "projects",
    "certifications", "objective", "summary",
]

EMAIL_PATTERN = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?\d{10}")
BULLET_PATTERN = re.compile(r"(^|\n)\s*[•\-\*]\s")


def calculate_ats_score(pdf_path, technical_skills):
    """Returns an integer 0-100 based on the actual content of the resume
    PDF at pdf_path, combined with the skills listed in the user's profile.
    Returns 0 if the file can't be read at all."""
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        print(f"[ATS SCORE ERROR] could not read {pdf_path}: {exc}")
        return 0

    word_count = len(text.split())

    # A near-empty extraction usually means a scanned/image-only PDF that
    # ATS systems genuinely can't parse either — score it low on purpose.
    if word_count < 50:
        return min(10, word_count // 5)

    text_lower = text.lower()
    score = 0

    # ---- Contact info (20 pts) -------------------------------------------
    if EMAIL_PATTERN.search(text):
        score += 10
    if PHONE_PATTERN.search(text):
        score += 10

    # ---- Standard section headers present (20 pts) ------------------------
    sections_found = sum(1 for kw in SECTION_KEYWORDS if kw in text_lower)
    score += min(sections_found * 5, 20)

    # ---- Overlap between resume text and the skills listed in profile (25 pts)
    if technical_skills:
        matched = sum(1 for skill in technical_skills if skill.lower() in text_lower)
        match_ratio = matched / len(technical_skills)
        score += round(match_ratio * 25)

    # ---- Healthy word count for a one-to-two page resume (15 pts) ---------
    if 300 <= word_count <= 1000:
        score += 15
    elif 150 <= word_count < 300 or 1000 < word_count <= 1500:
        score += 8

    # ---- Bullet point usage — ATS systems favor scannable bullets (10 pts)
    bullet_count = len(BULLET_PATTERN.findall(text))
    if bullet_count >= 5:
        score += 10
    elif bullet_count >= 1:
        score += 5

    # ---- Baseline for having extractable text at all (10 pts) -------------
    score += 10

    return min(score, 100)