import streamlit as st
import requests
from supabase import create_client

st.set_page_config(page_title="Login", page_icon="🔐")
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize Supabase
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)

# Session state
if "user_email" not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_role = None

# Redirect if already logged in
if st.session_state.user_email:
    st.switch_page("pages/app.py")
    st.stop()

st.title("🔐 Login with Email & Password")

with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password")
        else:
            # Firebase REST API for sign-in
            try:
                url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={st.secrets['FIREBASE_API_KEY']}"
                payload = {"email": email, "password": password, "returnSecureToken": True}
                res = requests.post(url, json=payload).json()

                if "error" in res:
                    st.error(res["error"]["message"])
                else:
                    # Check allowed_users in Supabase
                    user = supabase.table("allowed_users").select("*").eq("email", email).execute().data
                    if not user:
                        st.error("Unauthorized")
                    else:
                        st.session_state.user_email = email
                        st.session_state.user_role = user[0]["role"]
                        st.success(f"Logged in as {email}")
                        st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
