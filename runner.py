import streamlit as st
import os
import importlib

# Define the folder containing the pages
PAGES_FOLDER = "pages"

# Get the PORT from the environment (default to 8501 for local testing)
port = int(os.getenv("PORT", 8501))

# Function to dynamically load and collect all Streamlit pages in the folder
def load_pages(folder):
    pages = {}
    if not os.path.exists(folder):
        st.error(f"Error: The folder '{folder}' does not exist.")
        return pages

    for file_name in os.listdir(folder):
        if file_name.endswith(".py") and file_name != "runner.py":
            module_name = file_name[:-3]  # Remove the .py extension
            try:
                module = importlib.import_module(f"{folder}.{module_name}")
                pages[module_name] = module
            except Exception as e:
                st.error(f"Failed to load page {file_name}: {e}")
    return pages

# Load all pages from the specified folder
pages = load_pages(PAGES_FOLDER)

if not pages:
    st.warning("No pages available. Please check the 'pages' folder and ensure it contains valid Streamlit scripts.")
else:
    # Sidebar navigation
    st.sidebar.title("Navigation")
    selected_page = st.sidebar.radio("Go to", list(pages.keys()))

    # Display the selected page
    if selected_page in pages:
        pages[selected_page].data_exploration_page()

# This ensures the app runs on the correct port when deployed on Heroku
if __name__ == "__main__":
    # Start Streamlit with the appropriate port using os.system
    os.system(f"streamlit run runner.py --server.port={port} --server.address=0.0.0.0")
