import streamlit as st
import os
import importlib

# Define the folder containing the pages
PAGES_FOLDER = "pages"

# Function to dynamically load and collect all Streamlit pages in the folder
def load_pages(folder):
    pages = {}
    for file_name in os.listdir(folder):
        if file_name.endswith(".py") and file_name != "runner.py":
            module_name = file_name[:-3]  # Remove the .py extension
            module = importlib.import_module(f"{folder}.{module_name}")
            pages[module_name] = module
    return pages

# Load all pages from the specified folder
pages = load_pages(PAGES_FOLDER)

# Sidebar navigation
st.sidebar.title("Navigation")
selected_page = st.sidebar.radio("Go to", list(pages.keys()))

# Display the selected page
if selected_page in pages:
    pages[selected_page].data_exploration_page()
