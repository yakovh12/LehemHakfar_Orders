import os
import subprocess

# Define the paths to the main app and a secondary process
main_page_path = "all_pages.py"
secondary_script_path = os.path.join("pages")

# Check if the main app file exists
if not os.path.exists(main_page_path):
    raise FileNotFoundError(f"{main_page_path} not found!")

# Check if the secondary script exists
if not os.path.exists(secondary_script_path):
    raise FileNotFoundError(f"{secondary_script_path} not found!")

# Run the Streamlit app with the main page
print(f"Launching Streamlit app with {main_page_path}...")
subprocess.run(["streamlit", "run", main_page_path])

# Run a secondary subprocess (after the first one closes)
print(f"Launching secondary script with {secondary_script_path}...")
subprocess.run(["streamlit", "run", secondary_script_path])
