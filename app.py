import streamlit as st
import os
import shutil
import pandas as pd
import json
import re
from pathlib import Path
from PyPDF2 import PdfReader
import docx2txt
from word2number import w2n
import re

# Load requirements
with open("requirements.json", "r") as f:
    requirements = json.load(f)

MUST_HAVE = set([s.lower() for s in requirements.get("must_have", [])])
GOOD_TO_HAVE = set([s.lower() for s in requirements.get("good_to_have", [])])
MUST_NOT_HAVE = set([s.lower() for s in requirements.get("must_not_have", [])])
PREFERRED_TOOLS = set([s.lower() for s in requirements.get("preferred_tools", [])])
CERTIFICATIONS = set([s.lower() for s in requirements.get("certifications", [])])
DOMAIN_KEYWORDS = set([s.lower() for s in requirements.get("domain_keywords", [])])
MIN_EXPERIENCE = requirements.get("min_years_experience", 0)
EDUCATION_LEVEL = requirements.get("education_level", "bachelor").lower()
MIN_EDU_KEYWORDS = set([s.lower() for s in requirements.get("min_education_keywords", [])])
MIN_TOTAL_SCORE = requirements.get("min_total_score", 60)

CATEGORY_WEIGHTS = {
    "technical_skills": 60,
    "tools_and_tech": 20,
    "other": 20
}

LEVEL_THRESHOLDS = {
    "associate": {
        "must_have": 3,
        "good_to_have": 2,
        "tools": 2,
        "other": 2
    },
    "engineer": {
        "must_have": 5,
        "good_to_have": 3,
        "tools": 4,
        "other": 3
    },
    "senior": {
        "must_have": 6,
        "good_to_have": 4,
        "tools": 6,
        "other": 4
    }
}

def infer_job_level(exp):
    if exp < 2:
        return "associate"
    elif exp < 5:
        return "engineer"
    else:
        return "senior"

# ----------- CV Text Extraction -----------
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

def convert_written_numbers(text):
    words = text.split()
    converted_words = []
    i = 0
    while i < len(words):
        phrase = " ".join(words[i:i+3])
        try:
            number = w2n.word_to_num(phrase)
            converted_words.append(str(number))
            i += 3  # skip next two since already converted
        except:
            try:
                number = w2n.word_to_num(words[i])
                converted_words.append(str(number))
                i += 1
            except:
                converted_words.append(words[i])
                i += 1
    return " ".join(converted_words)
# ----------- Pattern Matching -----------
def match_components(text):
    found_must = [skill for skill in MUST_HAVE if skill.lower() in text]
    found_good = [skill for skill in GOOD_TO_HAVE if skill.lower() in text]
    found_cert = [cert for cert in CERTIFICATIONS if cert.lower() in text]
    found_domain = [kw for kw in DOMAIN_KEYWORDS if kw.lower() in text]
    found_preferred = [tool for tool in PREFERRED_TOOLS if tool.lower() in text]
    flagged_terms = [term for term in MUST_NOT_HAVE if term.lower() in text]
    missing_must = list(MUST_HAVE - set(found_must))
    other_traits = [kw for kw in ["collaboration", "communication", "ownership", "led", "mentored", "learner", "growth", "process improvement", "initiative"] if kw in text]
    return found_must, found_good, found_cert, found_domain, found_preferred, other_traits, flagged_terms, missing_must

# ----------- Experience Extraction -----------
def extract_years_experience(text):
    # Normalize the text
    text = text.lower()
    text = convert_written_numbers(text)

    # Flexible experience pattern
    pattern = r"""
        (?:(?:about|around|approximately|nearly|almost|more than|over|at least|less than)?\s*)?
        (?:(?:worked\s+for|possess(?:ed)?|gained|have|has|with)?\s*)?
        (\d+(?:\.\d+)?)\s*\+?\s*
        (?:years?|yrs?)\s*
        (?:of\s+)?(?:experience|expertise|exposure|background|practice|career)?
    """

    matches = re.findall(pattern, text, flags=re.IGNORECASE | re.VERBOSE)

    if matches:
        try:
            numbers = [float(m) for m in matches]
            return max(numbers)
        except:
            return 0
    return 0
# ----------- Education Extraction -----------
def extract_education(text):
    for keyword in MIN_EDU_KEYWORDS:
        if keyword in text:
            return keyword
    return "unknown"

# ----------- Scoring Logic -----------
def score_cv(found_must, found_good, found_cert, found_domain, found_preferred, other_traits, experience, education, flagged_terms, job_level):
    if flagged_terms:
        return 0, "Disqualified"

    expected = LEVEL_THRESHOLDS.get(job_level, LEVEL_THRESHOLDS["associate"])

    score = 0

    # TECHNICAL SKILLS
    must_score = (min(len(found_must), expected["must_have"]) / expected["must_have"]) * CATEGORY_WEIGHTS["technical_skills"]
    good_score = (min(len(found_good), expected["good_to_have"]) / expected["good_to_have"]) * 10
    score += must_score + good_score

    # TOOLS
    tools_found = len(found_preferred) + len(found_cert) + len(found_domain)
    tools_expected = expected["tools"]
    tool_score = (min(tools_found, tools_expected) / tools_expected) * CATEGORY_WEIGHTS["tools_and_tech"]
    score += tool_score

    # OTHER
    other_score = (min(len(other_traits), expected["other"]) / expected["other"]) * CATEGORY_WEIGHTS["other"]
    score += other_score

    # EXPERIENCE
    if experience >= MIN_EXPERIENCE:
        score += 3
    if job_level == "senior" and experience >= 5:
        score += 2

    # EDUCATION
    if education in MIN_EDU_KEYWORDS:
        score += 2

    remark = "Strong match" if score >= 80 else ("Moderate" if score >= MIN_TOTAL_SCORE else "Weak")
    return round(score, 2), remark

# ----------- Streamlit App -----------
def main():
    st.title("QA CV Filter – Auto-Level Inference")
    st.write("Upload multiple CVs. Score adjusts dynamically based on candidate experience level.")

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
            found_must, found_good, found_cert, found_domain, found_preferred, other_traits, flagged_terms, missing_must = match_components(text)
            experience = extract_years_experience(text)
            education = extract_education(text)
            job_level = infer_job_level(experience)
            score, remark = score_cv(found_must, found_good, found_cert, found_domain, found_preferred, other_traits, experience, education, flagged_terms, job_level)

            output.append({
                "Candidate": uploaded_file.name,
                "Job Level": job_level.title(),
                "Match %": score,
                "Remark": remark,
                "Missing Must-Have": ", ".join(missing_must),
                "Matched Good-To-Have": ", ".join(found_good),
                "Preferred Tools": ", ".join(found_preferred),
                "Certifications": ", ".join(found_cert),
                "Domains": ", ".join(found_domain),
                "Other Traits": ", ".join(other_traits),
                "Experience (Years)": experience,
                "Education": education.title(),
                "Red Flags": ", ".join(flagged_terms)
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
