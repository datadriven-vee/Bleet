import streamlit as st
import pandas as pd
import datetime
import re
from streamlit_mic_recorder import mic_recorder

# --- Helper Functions (Keep standard) ---
def get_ai_feedback(user_transcript, ideal_answer, question_text, groq_client):
    prompt = f"""
    Role: Senior Recruiter. Question: "{question_text}" Candidate Answer: "{user_transcript}"
    Task: Grade based on Relevance, STAR Structure, and Clarity. (Ref Strategy: "{ideal_answer}")
    OUTPUT: Score: [0-100], Verdict: [Strong Hire/Hire/No Hire], Feedback: [Advice]
    """
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

def parse_feedback(feedback_text):
    score = 0; verdict = "Pending"
    score_match = re.search(r"Score:\s*(\d+)", feedback_text, re.IGNORECASE)
    if score_match: score = int(score_match.group(1))
    verdict_match = re.search(r"Verdict:\s*(.+)", feedback_text, re.IGNORECASE)
    if verdict_match: verdict = verdict_match.group(1).strip()
    return score, verdict, feedback_text

# --- THE NEW UI VIEW ---
def view_problem_list(supabase):
    
    # 1. HEADER & PROGRESS SECTION
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown('<h1 class="glow-header">The Arena</h1>', unsafe_allow_html=True)
        st.caption("Master behavioral interviews. Grind questions. Get hired.")
    with c2:
        # Mock Progress Chart (Session Based)
        # We simulate progress for visual appeal since we don't have login yet
        solved = st.session_state.get('solved_count', 0)
        total = 50 
        progress = min(solved / total, 1.0)
        
        st.markdown(f"""
        <div class="chart-container">
            <h3 style="margin:0; color:#a78bfa;">Session Progress</h3>
            <h1 style="margin:0; font-size: 36px; color:white;">{int(progress*100)}%</h1>
            <p style="color:#64748b; font-size:12px;">{solved} / {total} Questions Conquered</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(progress)

    st.markdown("---")

    # 2. FETCH DATA
    response = supabase.table("questions").select("*").order("created_at", desc=True).limit(200).execute()
    df = pd.DataFrame(response.data)

    if df.empty:
        st.info("The Arena is empty. Go generate some questions!")
        return

    # 3. INTERACTIVE FILTERS ("Cloud" & Dropdown)
    col_filter_1, col_filter_2 = st.columns([2, 1])
    
    with col_filter_1:
        # The "Difficulty Cloud" - using a horizontal radio that we styled as tags in CSS
        st.markdown("**Select Difficulty Level**")
        diff_filter = st.radio(
            "Difficulty", 
            ["All", "Easy", "Medium", "Hard", "Expert"], 
            horizontal=True,
            label_visibility="collapsed"
        )
        
    with col_filter_2:
        # Clean Dropdown for Company
        st.markdown("**Target Company**")
        companies = ["All"] + sorted(list(df['company'].dropna().unique()))
        company_filter = st.selectbox("Company", companies, label_visibility="collapsed")

    # Apply Filters
    if company_filter != "All": df = df[df['company'] == company_filter]
    if diff_filter != "All": df = df[df['difficulty'] == diff_filter]

    # 4. PAGINATION LOGIC (Only show 10 at a time)
    ITEMS_PER_PAGE = 10
    if "page_number" not in st.session_state:
        st.session_state.page_number = 0

    # Calculate start/end indices
    total_pages = max(1, (len(df) // ITEMS_PER_PAGE) + (1 if len(df) % ITEMS_PER_PAGE > 0 else 0))
    # Ensure page number is valid
    if st.session_state.page_number >= total_pages: st.session_state.page_number = 0
    
    start_idx = st.session_state.page_number * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    
    # Slice the dataframe
    df_page = df.iloc[start_idx:end_idx]

    st.markdown(f"<p style='color:#64748b; margin-top: 20px;'>Showing {start_idx+1}-{min(end_idx, len(df))} of {len(df)} questions</p>", unsafe_allow_html=True)

    # 5. RENDER CARDS
    for index, row in df_page.iterrows():
        diff = row.get('difficulty', 'Medium') or 'Medium'
        role = row.get('role', 'General') or 'General'
        comp = row.get('company', 'Unknown') or 'Unknown'
        cat = row.get('category', 'Behavioral') or 'Behavioral'

        # Card Container
        with st.container():
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            
            with c1:
                st.markdown(f"""
                <div class="problem-row">
                    <div class="question-title">{row['question']}</div>
                    <div style="display: flex; align-items: center; margin-top: 10px; flex-wrap: wrap; gap: 8px;">
                        <span class="badge-base badge-{diff}">{diff}</span>
                        <span class="badge-base badge-blue">{cat}</span>
                        <span class="badge-base badge-gray">{comp}</span>
                        <span style="color: #94a3b8; font-size: 13px;">• {role}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                if st.button("Grind", key=f"btn_{row['id']}"):
                    q_id = row['id']
                    if isinstance(q_id, int):
                        full_q = supabase.table("questions").select("*").eq("id", q_id).single().execute()
                        st.session_state.selected_question = full_q.data
                    else:
                        st.session_state.selected_question = row.to_dict()
                    st.rerun()

    # 6. PAGINATION BUTTONS
    st.markdown("<br>", unsafe_allow_html=True)
    c_prev, c_mid, c_next = st.columns([1, 2, 1])
    
    with c_prev:
        if st.session_state.page_number > 0:
            if st.button("⬅️ Previous"):
                st.session_state.page_number -= 1
                st.rerun()
                
    with c_next:
        if st.session_state.page_number < total_pages - 1:
            if st.button("Next ➡️"):
                st.session_state.page_number += 1
                st.rerun()

# --- SOLVE PAGE (Kept simple, just ensuring it works) ---
def view_solve_page(supabase, groq_client):
    q = st.session_state.selected_question
    
    if st.button("⬅ Back to Arena"):
        st.session_state.selected_question = None
        st.rerun()
        
    st.markdown(f"### {q['question']}")
    st.divider()
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.info("💡 **Ideal Strategy:**\n\n" + q['ideal_answer'])
            
    with c2:
        st.write("🎙️ **Record Answer**")
        audio = mic_recorder(start_prompt="🔴 Record", stop_prompt="⏹️ Stop", key='recorder')
        
        if audio:
            st.audio(audio['bytes'])
            if st.button("Submit Answer", type="primary"):
                with st.spinner("Analyzing..."):
                    try:
                        # (Standard logic)
                        # Increment mock session progress
                        if 'solved_count' not in st.session_state: st.session_state.solved_count = 0
                        st.session_state.solved_count += 1
                        
                        # Transcribe & Grade logic (kept same as before)
                        with open("temp.wav", "wb") as f: f.write(audio['bytes'])
                        with open("temp.wav", "rb") as f:
                            transcript = groq_client.audio.transcriptions.create(file=("temp.wav", f.read()), model="whisper-large-v3").text
                        
                        raw_feedback = get_ai_feedback(transcript, q['ideal_answer'], q['question'], groq_client)
                        score, verdict, feedback = parse_feedback(raw_feedback)
                        
                        st.success("Complete!")
                        st.write(raw_feedback)
                        
                    except Exception as e:
                        st.error(f"Error: {e}")