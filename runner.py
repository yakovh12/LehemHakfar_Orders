import streamlit as st
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Load username and password from environment variables
USERNAME = os.getenv("USERNAME", "default_user")  # Default username for testing
PASSWORD = os.getenv("PASSWORD", "default_pass")  # Default password for testing

# Define the directory for pages
page_path = "pages"

# Check if the pages directory exists
if not os.path.exists(page_path):
    raise FileNotFoundError(f"{page_path} directory not found!")

# Function to verify login
def verify_login(username, password):
    return username == USERNAME and password == PASSWORD

# Login form
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if verify_login(username, password):
            st.success("Login successful!")
            st.session_state.logged_in = True
            st.session_state.username = username
        else:
            st.error("Invalid username or password.")
else:
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    # App content after login
    st.sidebar.title(f"Welcome, {st.session_state.username}!")
    st.sidebar.title("Navigation")

    # Ensure the default page is 'All Pages'
    default_page = "All Pages"

    # Check if the default page exists in the list
    if default_page.lower().replace(" ", "_") + ".py" not in os.listdir(page_path):
        raise FileNotFoundError(f"The default page '{default_page}' does not exist in the pages directory!")

    # Get all .py files in the pages directory, excluding 'runner'
    pages = [
        file.replace(".py", "").replace("_", " ").title()
        for file in os.listdir(page_path)
        if file.endswith(".py") and file != "runner.py"
    ]

    # Ensure the default page is included
    if default_page not in pages:
        pages.insert(0, default_page)

    # Pre-select 'All Pages' on the first load
    selected_page = st.sidebar.selectbox("Select a Page", pages, index=pages.index(default_page))

    # Display the selected page name
    st.write(f"### {selected_page}")
    st.write("This is the content for the selected page.")

    # Run the corresponding page (if dynamic loading is needed)
    page_file = selected_page.lower().replace(" ", "_") + ".py"
    page_file_path = os.path.join(page_path, page_file)

    if os.path.exists(page_file_path):
        exec(open(page_file_path).read())
    else:
        st.write("Selected page not found!")