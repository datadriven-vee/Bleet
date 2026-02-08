import streamlit as st
import streamlit_shadcn_ui as ui

def show_login_page(supabase_client):
    """
    Renders a professional Login Card centered on the screen.
    """
    # Load custom CSS
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Center the login card using columns
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown("## 🐑 Welcome to Bleet")
        st.caption("The AI-Powered Interview Coach tailored to your resume.")
        
        st.write("") # Spacer
        
        # GitHub Login Button (Styled exactly like Auth0)
        # NEW WORKING CODE
        response = supabase_client.auth.sign_in_with_oauth({
            "provider": "github",
            "options": {
                "redirect_to": "http://localhost:8501"
            }
        })
        auth_url = response.url
        
        # Custom HTML Button
        st.markdown(f'''
            <a href="{auth_url}" target="_self" style="text-decoration:none;">
                <div style="
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    background-color: #24292e; 
                    color: white; 
                    padding: 12px; 
                    border-radius: 6px; 
                    font-family: sans-serif;
                    font-weight: 500;
                    margin-bottom: 10px;
                    border: 1px solid #444;
                    transition: background 0.2s;">
                    <svg height="20" viewBox="0 0 16 16" version="1.1" width="20" aria-hidden="true" style="fill:white; margin-right:10px;">
                        <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
                    </svg>
                    Continue with GitHub
                </div>
            </a>
        ''', unsafe_allow_html=True)

        # "Fake" Google Button (Visual Placeholder)
        st.markdown(f'''
            <div style="
                display: flex; 
                align-items: center; 
                justify-content: center; 
                background-color: transparent; 
                color: #aaa; 
                padding: 12px; 
                border-radius: 6px; 
                font-family: sans-serif;
                font-weight: 500;
                border: 1px solid #444;
                cursor: not-allowed;">
                <svg xmlns="http://www.w3.org/2000/svg" height="20" viewBox="0 0 24 24" width="20" style="fill:#aaa; margin-right:10px;">
                    <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
                </svg>
                Continue with Google (Coming Soon)
            </div>
        ''', unsafe_allow_html=True)