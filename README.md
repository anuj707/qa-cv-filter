
# QA Engineer CV Filter (Streamlit App)

This free tool helps HR teams filter and rank CVs for QA Engineer positions.

## 🚀 How to Use (No Installation Required)
1. Upload this folder to a GitHub repository.
2. Go to [https://streamlit.io/cloud](https://streamlit.io/cloud)
3. Sign in with GitHub and click **“New App”**
4. Select the repository and `app.py`
5. Deploy and share the link with HR team.

## 🧾 Features
- Bulk upload CVs (PDF, DOCX, TXT)
- Auto extract skills, experience, education
- Match against `requirements.json`
- Score, rank and download CSV report

## 🛠 Requirements (for local use)
```bash
pip install streamlit pandas PyPDF2 docx2txt
streamlit run app.py
```
