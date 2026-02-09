import streamlit as st
import pandas as pd
import datetime
import re
import math
from streamlit_mic_recorder import mic_recorder

# --- Helper Functions ---
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

# --- THE LIBRARY VIEW ---
def view_problem_list(supabase):
    
    # 1. HEADER & PROGRESS
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown('<h1 class="glow-header">The Arena</h1>', unsafe_allow_html=True)
        st.caption("Master the behavioral grind. 10 questions at a time.")
    with c2:
        # Mock Session Progress
        solved = st.session_state.get('solved_count', 0)
        target = 10
        progress = min(solved / target, 1.0)
        
        st.markdown(f"""
        <div class="chart-container">
            <h3 style="margin:0; color:#a78bfa; font-size:14px;">Daily Goal</h3>
            <h1 style="margin:0; font-size: 32px; color:white;">{int(progress*100)}%</h1>
            <div style="background:#334155; height:6px; border-radius:3px; margin-top:5px;">
                <div style="background:#a78bfa; width:{int(progress*100)}%; height:100%; border-radius:3px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 2. FETCH DATA (Get everything so we can filter)
    # We fetch ID, Question, Company, Role, Difficulty, Category to display
    response = supabase.table("questions").select("*").order("created_at", desc=True).limit(200).execute()
    df = pd.DataFrame(response.data)

    if df.empty:
        st.info("The Arena is empty. Go generate some questions!")
        return

    # 3. FILTERS (Word Cloud Style & Dropdown)
    st.markdown("### 🎯 Filter Your Grind")
    
    col_cloud, col_drop = st.columns([2, 1])
    
    with col_cloud:
        # This renders as a horizontal list of buttons (Tag Cloud style via CSS)
        diff_filter = st.radio(
            "Difficulty Level", 
            ["All", "Easy", "Medium", "Hard", "Expert"], 
            horizontal=True,
            label_visibility="collapsed"
        )
        
    with col_drop:
        companies = ["All"] + sorted(list(df['company'].dropna().unique()))
        company_filter = st.selectbox("Target Company", companies, label_visibility="collapsed")

    # Apply Filters
    if company_filter != "All": df = df[df['company'] == company_filter]
    if diff_filter != "All": df = df[df['difficulty'] == diff_filter]

    # 4. PAGINATION LOGIC (10 Per Page)
    ITEMS_PER_PAGE = 10
    total_items = len(df)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    
    if "page_number" not in st.session_state: st.session_state.page_number = 0
    
    # Validation
    if st.session_state.page_number >= total_pages: st.session_state.page_number = 0
    
    start_idx = st.session_state.page_number * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    df_page = df.iloc[start_idx:end_idx]

    # Display count
    st.caption(f"Showing {start_idx + 1}-{min(end_idx, total_items)} of {total_items} questions")

    # 5. RENDER CARDS
    for index, row in df_page.iterrows():
        diff = row.get('difficulty', 'Medium') or 'Medium'
        role = row.get('role', 'General') or 'General'
        comp = row.get('company', 'Unknown') or 'Unknown'
        cat = row.get('category', 'Behavioral') or 'Behavioral'

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
                # THE FIX: We use a distinct key for every button
                if st.button("Start", key=f"btn_start_{row['id']}"):
                    # CRITICAL FIX: Fetch full data from DB to ensure 'ideal_answer' exists
                    # We handle both real IDs (int) and temp IDs (str)
                    q_id = row['id']
                    
                    if isinstance(q_id, int):
                        # Real DB Question -> Fetch fresh
                        data = supabase.table("questions").select("*").eq("id", q_id).single().execute()
                        st.session_state.selected_question = data.data
                    else:
                        # Temp/AI Question -> Use row data (already has ideal_answer)
                        st.session_state.selected_question = row.to_dict()
                        
                    st.rerun()

    # 6. PAGINATION CONTROLS
    st.markdown("<br>", unsafe_allow_html=True)
    if total_pages > 1:
        c_prev, c_mid, c_next = st.columns([1, 2, 1])
        with c_prev:
            if st.button("⬅️ Prev", disabled=(st.session_state.page_number == 0)):
                st.session_state.page_number -= 1
                st.rerun()
        with c_mid:
            st.markdown(f"<div style='text-align:center; padding-top:5px; color:#94a3b8;'>Page {st.session_state.page_number + 1} of {total_pages}</div>", unsafe_allow_html=True)
        with c_next:
            if st.button("Next ➡️", disabled=(st.session_state.page_number >= total_pages - 1)):
                st.session_state.page_number += 1
                st.rerun()

# --- SOLVE PAGE ---
def view_solve_page(supabase, groq_client):
    q = st.session_state.selected_question
    
    # Safety check
    if not q or 'ideal_answer' not in q:
        st.error("Error: Question data incomplete. Please go back.")
        if st.button("Back"):
            st.session_state.selected_question = None
            st.rerun()
        return

    # Header
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("⬅ Exit"):
            st.session_state.selected_question = None
            st.rerun()
            
    st.markdown(f"### {q['company']} - {q.get('role', 'Interview Question')}")
    
    # Question Box
    st.markdown(f"""
    <div style="background:rgba(30,41,59,0.5); padding:20px; border-radius:10px; border:1px solid #334155; margin-bottom:20px;">
        <h3 style="margin-top:0;">{q['question']}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Two columns: Strategy vs Recording
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.expander("💡 Show Ideal Answer Strategy", expanded=False):
            st.info(q['ideal_answer'])
            
    with c2:
        st.write("🎙️ **Record Your Answer**")
        audio = mic_recorder(start_prompt="🔴 Record", stop_prompt="⏹️ Stop", key='recorder')
        
        if audio:
            st.audio(audio['bytes'])
            if st.button("Submit Answer", type="primary"):
                with st.spinner("Analyzing..."):
                    try:
                        # 1. Update session progress
                        if 'solved_count' not in st.session_state: st.session_state.solved_count = 0
                        st.session_state.solved_count += 1
                        
                        # 2. Transcribe
                        with open("temp.wav", "wb") as f: f.write(audio['bytes'])
                        with open("temp.wav", "rb") as f:
                            transcript = groq_client.audio.transcriptions.create(file=("temp.wav", f.read()), model="whisper-large-v3").text
                        
                        # 3. Grade
                        raw_feedback = get_ai_feedback(transcript, q['ideal_answer'], q['question'], groq_client)
                        score, verdict, feedback = parse_feedback(raw_feedback)
                        
                        st.success("Analysis Complete!")
                        st.markdown(f"## Score: {score}/100")
                        st.write(raw_feedback)
                        
                    except Exception as e:
                        st.error(f"Error: {e}")