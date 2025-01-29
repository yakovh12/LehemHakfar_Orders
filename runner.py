import streamlit as st
import os
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from dotenv import load_dotenv
import base64
import json

# Load .env file
load_dotenv()

# Retrieve and decode Google OAuth JSON credentials
encoded_json = os.getenv("GOOGLE_CLIENT_SECRET_JSON")

if not encoded_json:
    raise ValueError("Error: GOOGLE_CLIENT_SECRET_JSON environment variable not found!")

# Parse JSON credentials directly into a dictionary
decoded_json = json.loads(base64.b64decode(encoded_json).decode("utf-8"))

# Use credentials dictionary instead of a file
flow = Flow.from_client_config(
    decoded_json,
    scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_uri="http://localhost:8501"
)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.title("Lehem Hakfar Orders")

if not st.session_state.logged_in:
    auth_url, _ = flow.authorization_url(prompt="consent")
    st.markdown(f'<a href="{auth_url}" target="_self"><button>Login with Google</button></a>', unsafe_allow_html=True)

    # Handle callback
    query_params = st.query_params

    if "code" in query_params:
        try:
            # Extract the code parameter
            auth_code = query_params.get("code")

            if auth_code:
                # Fetch token using the authorization code
                flow.fetch_token(code=auth_code)

                credentials = flow.credentials
                request = google.auth.transport.requests.Request()
                id_info = id_token.verify_oauth2_token(credentials.id_token, request)

                # Store user details in session state
                st.session_state.logged_in = True
                st.session_state.username = id_info["name"]
                st.session_state.email = id_info["email"]

                # Clear query parameters after login
                st.query_params.clear()

                # Force a rerun so that the else block executes
                st.rerun()

        except Exception as e:
            st.error(f"Login failed: {e}")

else:
    # Sidebar with logout button
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.username}!")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

        # Show available pages
        st.title("Navigation")
        page_path = "pages"

        if not os.path.exists(page_path):
            os.makedirs(page_path)

        pages = [f.replace(".py", "").replace("_", " ").title() for f in os.listdir(page_path) if f.endswith(".py")]

        if pages:
            default_page = "All Pages"  # Set your default page name
            if default_page in pages:
                default_index = pages.index(default_page)
            else:
                default_index = 0  # Fallback to the first option if the default is missing

            selected_page = st.selectbox("Select a Page", pages, index=default_index)

    # Ensure the page content is rendered in the main area, not the sidebar
    if selected_page:
        page_file = selected_page.lower().replace(" ", "_") + ".py"
        file_path = os.path.join(page_path, page_file)

        if os.path.exists(file_path):
            exec(open(file_path).read())  # Execute the selected page in the main content area

