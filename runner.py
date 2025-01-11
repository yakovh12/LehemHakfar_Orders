import streamlit as st
import os

# Define the directory for pages
page_path = "pages"

# Check if the pages directory exists
if not os.path.exists(page_path):
    raise FileNotFoundError(f"{page_path} directory not found!")

# Get all .py files in the pages directory, excluding 'runner'
pages = [
    file.replace(".py", "").replace("_", " ").title()
    for file in os.listdir(page_path)
    if file.endswith(".py") and file != "runner.py"
]

# Add a dropdown or sidebar for page selection
st.sidebar.title("Navigation")
selected_page = st.sidebar.selectbox("Select a Page", pages, index=2)

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

