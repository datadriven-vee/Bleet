import streamlit as st
import PyPDF2
import json
import random

def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def generate_custom_questions(resume_text, jd_text, groq_client):
    prompt = f"""
    You are a Bar Raiser at a top tech company. 
    JOB DESCRIPTION: {jd_text[:2000]}
    RESUME: {resume_text[:2000]}
    TASK: Generate exactly 10 PURELY BEHAVIORAL interview questions.
    CRITICAL RULES:
    1. NO TECHNICAL "HOW-TO". Focus on conflict, failure, leadership.
    2. Contextualize with resume projects.
    OUTPUT JSON ARRAY ONLY.
    """
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        result = json.loads(completion.choices[0].message.content)
        if isinstance(result, list): return result
        if "questions" in result: return result["questions"]
        if "interview_questions" in result: return result["interview_questions"]
        for k,v in result.items(): 
            if isinstance(v, list): return v
        return []
    except Exception as e:
        st.error(f"Generation Error: {e}")
        return []

def view_custom_generator(supabase, groq_client):
    st.title("⚡ Custom Interview Generator")
    st.markdown("Upload your resume and a job description. AI will generate **10 behavioral scenarios** tailored to you.")
    
    col1, col2 = st.columns(2)
    with col1:
        resume_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    with col2:
        jd_text = st.text_area("Paste Job Description", height=150, placeholder="Paste the full JD here...")

    if st.button("🚀 Generate & Enrich Database"):
        if not resume_file or not jd_text:
            st.warning("Please provide both Resume and JD.")
            return

        with st.spinner("Analyzing soft skills & culture fit..."):
            resume_text = extract_text_from_pdf(resume_file)
            generated_batch = generate_custom_questions(resume_text, jd_text, groq_client)
            
            if generated_batch:
                for q in generated_batch:
                    q['source_type'] = "User Generated"
                
                try:
                    data, count = supabase.table("questions").insert(generated_batch).execute()
                    st.session_state.generated_questions = generated_batch
                    st.success(f"🎉 Success! Generated {len(generated_batch)} behavioral scenarios.")
                except Exception as db_err:
                    st.error(f"Database Error: {db_err}")
            else:
                st.error("AI failed. Try again.")

    if st.session_state.generated_questions:
        st.divider()
        st.subheader("📝 Your New Custom Questions")
        for i, q in enumerate(st.session_state.generated_questions):
            with st.container():
                st.markdown(f"**Question {i+1}:** {q['question']}")
                if st.button(f"Practice Question {i+1} ➡️", key=f"btn_{i}"):
                    db_row = supabase.table("questions").select("*").eq("question", q['question']).limit(1).single().execute()
                    st.session_state.selected_question = db_row.data
                    st.rerun()
                st.divider()