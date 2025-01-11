import streamlit as st


# App title
st.title("Welcome to the Order Application")

# List of pages and their explanations
pages_info = [
    {"name": "Create Order", "description": "Create a new order with the necessary details."},
    {"name": "Delete Order", "description": "Delete an existing order by providing its ID or details."},
    {"name": "View Orders", "description": "View all existing orders along with their statuses."},
]

# Display the list of pages and explanations
st.subheader("Pages Description:")
for page in pages_info:
    st.write(f"**{page['name']}**: {page['description']}")
