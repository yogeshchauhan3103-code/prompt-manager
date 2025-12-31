import streamlit as st
import requests
from supabase import create_client

st.set_page_config(page_title="Login", page_icon="🔐")


supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)

if "user_email" not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_role = None

if st.session_state.user_email:
    st.switch_page("pages/app.py")
    st.stop()


def send_magic_link(email):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={st.secrets['FIREBASE_API_KEY']}"
    payload = {
        "requestType": "EMAIL_SIGNIN",
        "email": email,
        "continueUrl": f"{st.secrets['APP_URL']}/app.py",
        "canHandleCodeInApp": True
    }
    return requests.post(url, json=payload).json()


def complete_login(oob_code):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink?key={st.secrets['FIREBASE_API_KEY']}"
    return requests.post(url, json={"oobCode": oob_code}).json()


# Handle magic link redirect
params = st.query_params
if "oobCode" in params:
    result = complete_login(params["oobCode"])
    if "email" in result:
        user = supabase.table("allowed_users").select("*").eq("email", result["email"]).execute().data
        if not user:
            st.error("Unauthorized")
            st.stop()

        st.session_state.user_email = result["email"]
        st.session_state.user_role = user[0]["role"]
        st.query_params = {}
        st.switch_page("pages/app.py")
    else:
        st.error("Login failed")
        st.stop()


st.title("🔐 Login")

email = st.text_input("Company Email")

if st.button("Send Magic Link"):
    allowed = supabase.table("allowed_users").select("email").eq("email", email).execute().data
    if not allowed:
        st.error("Not authorized")
    else:
        send_magic_link(email)
        st.success("Magic link sent. Check your email.")
