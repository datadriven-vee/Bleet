import streamlit as st
import pandas as pd
from supabase import create_client, Client
from groq import Groq

# IMPORT VIEWS (Removed auth_view)
from views.generator_view import view_custom_generator
from views.library_view import view_problem_list, view_solve_page

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Bleet", layout="wide", page_icon="🐑")

# Initialize Clients
@st.cache_resource
def init_clients():
    try:
        # We still need these to fetch questions and generate AI answers
        supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
        return supabase, groq
    except Exception as e:
        st.error(f"Failed to connect to cloud services: {e}")
        return None, None

supabase, groq_client = init_clients()

# Session State Initialization
if "selected_question" not in st.session_state:
    st.session_state.selected_question = None
if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []

# --- 2. MAIN APP CONTROLLER (No Login Check) ---

def main():
    # Sidebar Navigation
    with st.sidebar:
        st.title("🐑 Bleet")
        st.caption("Guest Mode (No Login Required)")
        st.divider()
        mode = st.radio("Mode", ["Library Practice", "Custom Generator"])
        st.divider()
        
        # Optional: Reset button if things get stuck
        if st.button("Reset App"):
            st.session_state.selected_question = None
            st.rerun()

    # ROUTING LOGIC
    if st.session_state.selected_question:
        # User selected a question -> Show Solve Page
        view_solve_page(supabase, groq_client)
        
    elif mode == "Custom Generator":
        # User wants to generate questions -> Show Generator
        view_custom_generator(supabase, groq_client)
        
    else:
        # Default -> Show Library
        view_problem_list(supabase)

if __name__ == "__main__":
    main()