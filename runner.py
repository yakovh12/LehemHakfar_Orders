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

# Display a large title on the main page
st.markdown("<h1 style='text-align: center;'>Welcome to LehemHakfar Order App</h1>", unsafe_allow_html=True)


