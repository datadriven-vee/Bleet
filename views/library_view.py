import streamlit as st
import pandas as pd
import datetime
import re
from streamlit_mic_recorder import mic_recorder

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

def view_problem_list(supabase):
    st.title("📚 Question Library")
    
    # Use st.cache_data correctly within the view
    response = supabase.table("questions").select("*").order("created_at", desc=True).limit(500).execute()
    df = pd.DataFrame(response.data)

    if df.empty:
        st.warning("Database empty.")
        return

    with st.sidebar:
        st.header("🔍 Filter Library")
        companies = ["All"] + sorted([str(x) for x in df['company'].unique() if x is not None])
        company = st.selectbox("Company", companies)
    
    if company != "All": df = df[df['company'] == company]

    selection = st.dataframe(
        df[['company', 'role', 'difficulty', 'question']],
        use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun"
    )

    if selection and len(selection.selection['rows']) > 0:
        row_idx = selection.selection['rows'][0]
        st.session_state.selected_question = df.iloc[row_idx].to_dict()
        st.rerun()

def view_solve_page(supabase, groq_client):
    q = st.session_state.selected_question
    
    c1, c2 = st.columns([1, 6])
    if c1.button("⬅️ Exit"):
        st.session_state.selected_question = None
        st.rerun()
    c2.subheader(f"{q['company']} - {q['role']}")
    st.divider()
    
    left, right = st.columns([1, 1])
    with left:
        st.info(f"**Question:** {q['question']}")
        with st.expander("Show Ideal Answer"):
            st.write(q['ideal_answer'])
            
    with right:
        st.write("🎙️ **Record Answer**")
        audio = mic_recorder(start_prompt="🔴 Record", stop_prompt="⏹️ Stop", key='recorder')
        
        if audio:
            st.audio(audio['bytes'])
            if st.button("Submit for Grading"):
                with st.spinner("Grading..."):
                    try:
                        with open("temp.wav", "wb") as f: f.write(audio['bytes'])
                        with open("temp.wav", "rb") as f:
                            transcript = groq_client.audio.transcriptions.create(file=("temp.wav", f.read()), model="whisper-large-v3").text
                        
                        raw_feedback = get_ai_feedback(transcript, q['ideal_answer'], q['question'], groq_client)
                        score, verdict, feedback = parse_feedback(raw_feedback)
                        
                        path = f"{q['id']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
                        supabase.storage.from_("submissions").upload(path, audio['bytes'], {"content-type": "audio/wav"})
                        url = supabase.storage.from_("submissions").get_public_url(path)
                        
                        supabase.table("submissions").insert({
                            "question_id": q['id'], 
                            "transcript": transcript, 
                            "ai_score": score, 
                            "ai_feedback": raw_feedback, 
                            "ai_verdict": verdict, 
                            "audio_url": url,
                        }).execute()
                        
                        st.success("Saved!")
                        st.write(raw_feedback)
                    except Exception as e:
                        st.error(f"Error: {e}")