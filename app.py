import streamlit as st
import pandas as pd
from supabase import create_client, Client
from streamlit_mic_recorder import mic_recorder
from groq import Groq
import os
import re
import datetime
import json
import PyPDF2
import random

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Bleet", layout="wide", page_icon="🐑")

# Initialize Clients
@st.cache_resource
def init_clients():
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
    return supabase, groq

supabase, groq_client = init_clients()

# --- website design call ---
def load_css():
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css() 

# Session State
if "selected_question" not in st.session_state:
    st.session_state.selected_question = None
if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []

# --- 2. LOGIC FUNCTIONS ---

def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def generate_custom_questions(resume_text, jd_text):
    """
    Uses Llama 3 to generate 10 HIGH-SPECIFICITY behavioral questions.
    It forces the AI to reference specific resume projects/tools to avoid generic questions.
    """
    prompt = f"""
    You are a "Bar Raiser" interviewer at a top tech company (like Amazon or Google).
    I will provide a Candidate's Resume and a Job Description.

    ### CANDIDATE RESUME
    {resume_text[:2500]}

    ### JOB DESCRIPTION
    {jd_text[:2500]}

    ### YOUR GOAL
    Generate 7 TOUGH behavioral interview questions. 
    
    ### CRITICAL RULES (Follow these or you fail):
    1. **NO GENERIC QUESTIONS:** Do NOT ask "Tell me about a time you worked in a team."
    2. **USE RESUME DETAILS:** You MUST mention a specific project, tool, or experience from the resume in every question.
       - *Bad:* "Tell me about a challenge."
       - *Good:* "In your 'InsightBot' project, you used LangChain. Tell me about a specific limitation you found in LangChain and how you worked around it."
    3. **FOCUS ON FAILURE & CONFLICT:**
       - Ask about missed deadlines.
       - Ask about disagreeing with a manager.
       - Ask about a technical tradeoff that went wrong.
    4. **JOB ALIGNMENT:**
       - If the JD requires "Snowflake", ask: "Tell me about a time you had to optimize a slow SQL query in Snowflake or a similar DB. What was the bottleneck?"

    ### OUTPUT FORMAT
    Return ONLY a raw JSON array. No markdown.
    [
        {{
            "company": "Company Name from JD",
            "role": "Role Title from JD",
            "difficulty": "Hard",
            "category": "Conflict" OR "Failure" OR "Leadership" OR "Technical_Tradeoff",
            "question": "The specific question referencing resume details...",
            "ideal_answer": "Brief STAR guide: Situation (The specific project), Task, Action (What they specifically did), Result."
        }},
        ... (7 items)
    ]
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, 
            response_format={"type": "json_object"}
        )
        result = json.loads(completion.choices[0].message.content)
        
        # Robust JSON extraction
        if isinstance(result, list): return result
        if "questions" in result: return result["questions"]
        if "interview_questions" in result: return result["interview_questions"]
        
        # Fallback search
        for key, value in result.items():
            if isinstance(value, list): return value
        return []
            
    except Exception as e:
        st.error(f"Generation Error: {e}")
        return []

def get_ai_feedback(user_transcript, ideal_answer, question_text):
    prompt = f"""
    Role: Senior Recruiter.
    Question: "{question_text}"
    Candidate Answer: "{user_transcript}"
    
    Task: Grade based on Relevance, STAR Structure, and Clarity.
    (Ref Answer Strategy: "{ideal_answer}")
    
    OUTPUT FORMAT:
    Score: [0-100]
    Verdict: [Strong Hire / Hire / Weak Hire / No Hire]
    Feedback: [Specific advice]
    """
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

def parse_feedback(feedback_text):
    score = 0
    verdict = "Pending"
    score_match = re.search(r"Score:\s*(\d+)", feedback_text, re.IGNORECASE)
    if score_match: score = int(score_match.group(1))
    verdict_match = re.search(r"Verdict:\s*(.+)", feedback_text, re.IGNORECASE)
    if verdict_match: verdict = verdict_match.group(1).strip()
    return score, verdict, feedback_text

# --- 3. UI VIEWS ---

def view_custom_generator():
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
            generated_batch = generate_custom_questions(resume_text, jd_text)
            
            if generated_batch and len(generated_batch) > 0:
                # Tag as User Generated
                for q in generated_batch:
                    q['source_type'] = "User Generated"
                
                try:
                    # Save ALL generated questions to DB so they can be practiced
                    data, count = supabase.table("custom_questions").insert(generated_batch).execute()
                    st.session_state.generated_questions = generated_batch
                    st.success(f"🎉 Success! Generated and saved {len(generated_batch)} behavioral scenarios.")
                except Exception as db_err:
                    st.error(f"Database Error: {db_err}")
            else:
                st.error("AI failed to generate valid questions. Please try again.")

    # Display Generated Questions
    if st.session_state.generated_questions:
        st.divider()
        st.subheader("📝 Your New Custom Questions")
        
        for i, q in enumerate(st.session_state.generated_questions):
            with st.container():
                st.markdown(f"**Question {i+1}:** {q['question']}")
                st.caption(f"Category: {q['category']} | Difficulty: {q['difficulty']}")
                if st.button(f"Practice Question {i+1} ➡️", key=f"btn_{i}"):
                    # Fetch ID for submission tracking
                    db_row = supabase.table("questions").select("*").eq("question", q['question']).limit(1).single().execute()
                    st.session_state.selected_question = db_row.data
                    st.rerun()
                st.divider()


def view_problem_list():
    st.title("Think Clear, Be You")
    
    # Fetch Data
    @st.cache_data(ttl=5) 
    def fetch_questions():
        response = supabase.table("questions").select("id, question, company, role, difficulty, category").order("created_at", desc=True).limit(500).execute()
        return pd.DataFrame(response.data)

    df = fetch_questions()
    
    if df.empty:
        st.warning("Database empty.")
        return

    # Filters
    with st.sidebar:
        st.header("🔍 Filter Library")
        # Filter Logic (Handles None values)
        companies = ["All"] + sorted([str(x) for x in df['company'].unique() if x is not None])
        roles = ["All"] + sorted([str(x) for x in df['role'].unique() if x is not None])
        
        company = st.selectbox("Company", companies)
        role = st.selectbox("Role", roles)

    # Apply Filters
    if company != "All": df = df[df['company'] == company]
    if role != "All": df = df[df['role'] == role]

    # Table
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Render Cards with Centered Buttons
    for index, row in df.iterrows():
        # Handle defaults
        diff = row.get('difficulty', 'Medium') or 'Medium'
        role = row.get('role', 'General') or 'General'
        comp = row.get('company', 'Unknown') or 'Unknown'
        cat = row.get('category', 'Behavioral') or 'Behavioral'

        # THE FIX: Use vertical_alignment="center" to align text and button
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        
        with c1:
            # The Card Content
            st.markdown(f"""
            <div class="problem-row" style="margin-bottom: 0px; border-right: none;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="flex-grow:1;">
                        <span class="question-title">{row['question']}</span>
                        <div style="margin-top:6px;">
                            <span class="badge-base badge-{diff}">{diff}</span>
                            <span class="badge-base badge-blue">{cat}</span>
                            <span class="badge-base badge-gray">{comp}</span>
                            <span class="meta-text" style="color: #64748b; font-size: 13px; margin-left: 8px;">• {role}</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            # The Button (Updated Logic)
            if st.button("Start", key=f"btn_{row['id']}"):
                # Force fetch the full question (including ideal_answer) from DB
                # Note: We cast row['id'] to int just to be safe, but the query handles it.
                full_q = supabase.table("questions").select("*").eq("id", row['id']).single().execute()
                st.session_state.selected_question = full_q.data
                st.rerun()
        
        # Add a subtle separator
        st.markdown("<hr style='margin: 8px 0; border-color: #334155; opacity: 0.3;'>", unsafe_allow_html=True)


def view_solve_page():
    q = st.session_state.selected_question
    
    # Header
    c1, c2 = st.columns([1, 6])
    if c1.button("⬅️ Exit"):
        st.session_state.selected_question = None
        st.rerun()
    c2.subheader(f"{q['company']} - {q['role']}")
    
    st.divider()
    
    left, right = st.columns([1, 1])
    with left:
        st.info(f"**Question:** {q['question']}")
        with st.expander("Show Ideal Answer Strategy"):
            st.write(q['ideal_answer'])
            
    with right:
        st.write("🎙️ **Record Answer**")
        audio = mic_recorder(start_prompt="🔴 Record", stop_prompt="⏹️ Stop", key='recorder')
        
        if audio:
            st.audio(audio['bytes'])
            if st.button("Submit for Grading"):
                with st.spinner("Grading..."):
                    try:
                        # 1. Transcribe
                        with open("temp.wav", "wb") as f: f.write(audio['bytes'])
                        with open("temp.wav", "rb") as f:
                            transcript = groq_client.audio.transcriptions.create(file=("temp.wav", f.read()), model="whisper-large-v3").text
                        
                        # 2. Grade
                        raw_feedback = get_ai_feedback(transcript, q['ideal_answer'], q['question'])
                        score, verdict, feedback = parse_feedback(raw_feedback)
                        
                        # 3. Save
                        path = f"{q['id']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
                        supabase.storage.from_("submissions").upload(path, audio['bytes'], {"content-type": "audio/wav"})
                        url = supabase.storage.from_("submissions").get_public_url(path)
                        
                        supabase.table("submissions").insert({
                            "question_id": q['id'], "transcript": transcript, 
                            "ai_score": score, "ai_feedback": raw_feedback, 
                            "ai_verdict": verdict, "audio_url": url
                        }).execute()
                        
                        st.success("Saved!")
                        c1, c2 = st.columns(2)
                        c1.metric("Score", score)
                        c2.metric("Verdict", verdict)
                        st.write(raw_feedback)
                    except Exception as e:
                        st.error(f"Error processing submission: {e}")

# --- 4. MAIN ROUTER ---

# Sidebar Navigation
# --- 4. MAIN ROUTER ---

# Callback to close the question when you switch modes
def reset_question_state():
    st.session_state.selected_question = None

# Sidebar Navigation
with st.sidebar:
    st.title("🐑 Bleet")
    # ADDED: on_change=reset_question_state
    mode = st.radio(
        "Mode", 
        ["Library Practice", "Custom Generator"], 
        on_change=reset_question_state
    )
    st.divider()

if st.session_state.selected_question:
    view_solve_page()
elif mode == "Custom Generator":
    view_custom_generator()
else:
    view_problem_list()