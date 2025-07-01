import streamlit as st
import os
import shutil
import pandas as pd
import json
import re
from pathlib import Path
from PyPDF2 import PdfReader
import docx2txt

# Load requirements
with open("requirements.json", "r") as f:
    requirements = json.load(f)

MUST_HAVE = set([s.lower() for s in requirements["must_have"]])
GOOD_TO_HAVE = set([s.lower() for s in requirements["good_to_have"]])
MUST_NOT_HAVE = set([s.lower() for s in requirements.get("must_not_have", [])])
PREFERRED_TOOLS = set([s.lower() for s in requirements.get("preferred_tools", [])])
CERTIFICATIONS = set([s.lower() for s in requirements.get("certifications", [])])
DOMAIN_KEYWORDS = set([s.lower() for s in requirements.get("domain_keywords", [])])
REQUIRED_TOOLS_COUNT = requirements.get("required_tools_count", 0)
MIN_EXPERIENCE = requirements["min_years_experience"]
EDUCATION_LEVEL = requirements["education_level"].lower()
MIN_EDU_KEYWORDS = set([s.lower() for s in requirements.get("min_education_keywords", [])])
MIN_TOTAL_SCORE = requirements.get("min_total_score", 0)


def extract_text(file_path):
    if file_path.suffix == ".pdf":
        text = ""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except:
            text = ""
        return text.lower()
    elif file_path.suffix == ".docx":
        try:
            return docx2txt.process(str(file_path)).lower()
        except:
            return ""
    elif file_path.suffix == ".txt":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().lower()
        except:
            return ""
    return ""


def match_skills(text):
    found_must = [skill for skill in MUST_HAVE if skill in text]
    found_good = [skill for skill in GOOD_TO_HAVE if skill in text]
    found_cert = [cert for cert in CERTIFICATIONS if cert in text]
    found_domain = [kw for kw in DOMAIN_KEYWORDS if kw in text]
    found_preferred = [tool for tool in PREFERRED_TOOLS if tool in text]
    flagged_terms = [term for term in MUST_NOT_HAVE if term in text]
    missing_must = list(MUST_HAVE - set(found_must))
    return found_must, found_good, found_cert, found_domain, found_preferred, flagged_terms, missing_must


def extract_years_experience(text):
    pattern = r"""
        (?:(?:about|around|approximately|nearly|almost|more than|over|at least|less than)?\s*)?
        (?:(?:worked\s+for|possess(?:ed)?|gained|total|with\s+a\s+background\s+spanning)?\s*)?
        (\d+(?:\.\d+)?)\s*\+?\s*
        (?:years?|yrs?)\s*
        (?:of\s+(?:industry\s+|professional\s+)?experience)?
    """
    matches = re.findall(pattern, text, flags=re.IGNORECASE | re.VERBOSE)
    if matches:
        try:
            numbers = [float(m) for m in matches]
            return max(numbers)
        except:
            return 0
    return 0


def extract_education(text):
    for keyword in MIN_EDU_KEYWORDS:
        if keyword in text:
            return keyword
    return "unknown"


def score_cv(found_must, found_good, found_cert, found_domain, found_preferred, experience, education, flagged_terms):
    if flagged_terms:
        return 0  # Disqualify immediately if any red-flag terms found

    score = 0
    if MUST_HAVE:
        score += (len(found_must) / len(MUST_HAVE)) * 60
    if GOOD_TO_HAVE:
        score += (len(found_good) / len(GOOD_TO_HAVE)) * 15
    if PREFERRED_TOOLS:
        score += (len(found_preferred) / len(PREFERRED_TOOLS)) * 5
    if CERTIFICATIONS:
        score += (len(found_cert) / len(CERTIFICATIONS)) * 5
    if DOMAIN_KEYWORDS:
        score += (len(found_domain) / len(DOMAIN_KEYWORDS)) * 5
    if experience >= MIN_EXPERIENCE:
        score += 5
    if education in MIN_EDU_KEYWORDS:
        score += 5

    return round(score, 2)


def main():
    st.title("QA Engineer CV Filter")
    st.write("Upload multiple CVs and match them with your QA Engineer requirements.")

    uploaded_files = st.file_uploader("Upload CVs (PDF, DOCX, TXT)", accept_multiple_files=True)

    if uploaded_files:
        output = []
        temp_dir = Path("temp_resumes")
        temp_dir.mkdir(exist_ok=True)

        for uploaded_file in uploaded_files:
            file_path = temp_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            text = extract_text(file_path)
            found_must, found_good, found_cert, found_domain, found_preferred, flagged_terms, missing_must = match_skills(text)
            experience = extract_years_experience(text)
            education = extract_education(text)
            score = score_cv(found_must, found_good, found_cert, found_domain, found_preferred, experience, education, flagged_terms)

            output.append({
                "Candidate": uploaded_file.name,
                "Match %": score,
                "Missing Must-Have": ", ".join(missing_must),
                "Matched Good-To-Have": ", ".join(found_good),
                "Preferred Tools": ", ".join(found_preferred),
                "Certifications": ", ".join(found_cert),
                "Domains": ", ".join(found_domain),
                "Experience (Years)": experience,
                "Education": education.title(),
                "Red Flags": ", ".join(flagged_terms),
                "Remarks": "Strong match" if score >= 80 else ("Moderate" if score >= MIN_TOTAL_SCORE else "Weak or Disqualified")
            })

        shutil.rmtree(temp_dir)

        df = pd.DataFrame(output)
        st.dataframe(df)

        csv_path = "output/cv_matching_report.csv"
        Path("output").mkdir(exist_ok=True)
        df.to_csv(csv_path, index=False)
        st.download_button("Download Report as CSV", data=open(csv_path, "rb"), file_name="cv_report.csv")


if __name__ == "__main__":
    main()
