import streamlit as st
import pandas as pd
import datetime
import re
from streamlit_mic_recorder import mic_recorder

# --- Helper Functions (Keep standard) ---
def get_ai_feedback(user_transcript, ideal_answer, question_text, groq_client):
    prompt = f"""
    Role: Senior Recruiter.
    Question: "{question_text}"
    Candidate Answer: "{user_transcript}"
    Task: Grade based on Relevance, STAR Structure, and Clarity.
    (Ref Answer Strategy: "{ideal_answer}")
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

# --- THE MAIN VIEW ---
# ... (Imports and helper functions stay the same) ...

def view_problem_list(supabase):
    # Header with a bit more spacing
    st.markdown("<h1 style='margin-bottom: 20px;'>📚 Problem Library</h1>", unsafe_allow_html=True)
    
    # 1. Fetch Data
    response = supabase.table("questions").select("*").order("created_at", desc=True).limit(50).execute()
    df = pd.DataFrame(response.data)

    if df.empty:
        st.info("Database is empty. Go generate some questions!")
        return

    # 2. Refined Filter Bar
    with st.expander("🔍 **Filter Questions**", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            company_filter = st.selectbox("Company", ["All"] + sorted(list(df['company'].dropna().unique())))
        with c2:
            role_filter = st.selectbox("Role", ["All"] + sorted(list(df['role'].dropna().unique())))
        with c3:
            diff_filter = st.selectbox("Difficulty", ["All", "Easy", "Medium", "Hard"])

    # Apply Filters
    if company_filter != "All": df = df[df['company'] == company_filter]
    if role_filter != "All": df = df[df['role'] == role_filter]
    if diff_filter != "All": df = df[df['difficulty'] == diff_filter]

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Render "Classic" Cards
    for index, row in df.iterrows():
        # Defaults
        diff = row.get('difficulty', 'Medium') or 'Medium'
        role = row.get('role', 'General') or 'General'
        cat = row.get('category', 'Behavioral') or 'Behavioral'
        comp = row.get('company', 'Unknown') or 'Unknown'
        
        # We use the 'problem-row' class from our new CSS
        # Note: We WRAP the container in a div with that class using markdown
        
        with st.container():
            # Open the CSS card styling
            st.markdown(f"""
            <div class="problem-row">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="flex-grow:1;">
                        <span class="question-title">{row['question']}</span>
                        <div style="margin-top:6px;">
                            <span class="badge-base badge-{diff}">{diff}</span>
                            <span class="badge-base badge-blue">{cat}</span>
                            <span class="badge-base badge-gray">{comp}</span>
                            <span class="meta-text" style="margin-left:8px;">• {role}</span>
                        </div>
                    </div>
                    </div>
            </div>
            """, unsafe_allow_html=True)
            
            # The button needs to be native Streamlit to work, so we place it "visually" nearby
            # This is a trick: We put the button in a column that floats to the right
            # But since we can't inject the button INTO the HTML string, we use columns above 
            # effectively. Let's do the column layout cleanly:
            
    # --- BETTER LAYOUT APPROACH FOR CARDS ---
    for index, row in df.iterrows():
        diff = row.get('difficulty', 'Medium') or 'Medium'
        role = row.get('role', 'General')
        cat = row.get('category', 'Behavioral')
        comp = row.get('company', 'Unknown')

        # Outer Card Container
        with st.container():
            st.markdown('<div class="problem-row">', unsafe_allow_html=True)
            
            c1, c2 = st.columns([5, 1])
            
            with c1:
                st.markdown(f"""
                <div class="question-title">{row['question']}</div>
                <div style="margin-top: 8px;">
                    <span class="badge-base badge-{diff}">{diff}</span>
                    <span class="badge-base badge-blue">{cat}</span>
                    <span class="badge-base badge-gray">{comp} • {role}</span>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                # Centering the button vertically
                st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True) 
                if st.button("Start", key=f"btn_{row['id']}"):
                    st.session_state.selected_question = row.to_dict()
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

# --- SOLVE PAGE (Kept simple) ---
def view_solve_page(supabase, groq_client):
    q = st.session_state.selected_question
    
    if st.button("⬅ Exit Practice"):
        st.session_state.selected_question = None
        st.rerun()
        
    st.markdown(f"### {q['question']}")
    
    # Metadata Header
    st.markdown(f"""
    <span class="badge-base badge-{q.get('difficulty','Medium')}">{q.get('difficulty','Medium')}</span>
    <span class="badge-base badge-gray">{q.get('company','')}</span>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.info("💡 **Ideal Answer Strategy:**\n\n" + q['ideal_answer'])
            
    with c2:
        st.write("🎙️ **Record Answer**")
        audio = mic_recorder(start_prompt="🔴 Record", stop_prompt="⏹️ Stop", key='recorder')
        
        if audio:
            st.audio(audio['bytes'])
            if st.button("Get AI Feedback", type="primary"):
                with st.spinner("Analyzing..."):
                    try:
                        # 1. Transcribe (Always do this)
                        with open("temp.wav", "wb") as f: f.write(audio['bytes'])
                        with open("temp.wav", "rb") as f:
                            transcript = groq_client.audio.transcriptions.create(file=("temp.wav", f.read()), model="whisper-large-v3").text
                        
                        # 2. Grade (Always do this)
                        raw_feedback = get_ai_feedback(transcript, q['ideal_answer'], q['question'], groq_client)
                        score, verdict, feedback = parse_feedback(raw_feedback)
                        
                        st.success("Analysis Complete!")
                        st.markdown(f"### Score: {score}/100")
                        st.write(raw_feedback)

                        # --- CHANGE START: Only save if it's a REAL question ---
                        # We check if the ID is an integer (Real DB ID) or a string "temp_x" (Fake ID)
                        if isinstance(q['id'], int):
                            path = f"{q['id']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
                            supabase.storage.from_("submissions").upload(path, audio['bytes'], {"content-type": "audio/wav"})
                            url = supabase.storage.from_("submissions").get_public_url(path)
                            
                            supabase.table("submissions").insert({
                                "question_id": q['id'], "transcript": transcript, 
                                "ai_score": score, "ai_feedback": raw_feedback, 
                                "ai_verdict": verdict, "audio_url": url
                            }).execute()
                            st.toast("Saved to history!", icon="💾")
                        else:
                            st.warning("Temporary question: Result shown but not saved to database.")
                        # --- CHANGE END ---

                    except Exception as e:
                        st.error(f"Error: {e}")