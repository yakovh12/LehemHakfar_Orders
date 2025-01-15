import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL database connection details
DATABASE_URL = os.environ.get("DATABASE_URL")

# Function to connect to PostgreSQL and fetch data
def fetch_data_from_postgres(query):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Function to execute a query in PostgreSQL
def execute_query(query, params=None):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    cursor.close()
    conn.close()

# Fetch customers data
@st.cache_data
def get_customers():
    query = "SELECT customer_id, customer_name FROM customers;"
    return fetch_data_from_postgres(query)

# Fetch customer prompts data with customer names
@st.cache_data
def get_customer_prompts():
    query = """
    SELECT cp.customer_id, c.customer_name, cp.open_ai_prompt
    FROM customer_prompts cp
    LEFT JOIN customers c ON cp.customer_id = c.customer_id;
    """
    return fetch_data_from_postgres(query)

# Main Streamlit app
def main():
    st.title("Customer Prompts Manager")

    # Button to refresh data
    if st.button("Refresh Data"):
        st.cache_data.clear()

    # Fetch customers data
    customers = get_customers()

    # Create a dropdown for selecting customers to filter
    customers["display"] = customers.apply(lambda x: f"{x['customer_id']} - {x['customer_name']}", axis=1)
    filter_customer = st.selectbox(
        "Filter by Customer (ID - Name)",
        options=["All"] + customers["display"].tolist(),
    )

    # Fetch customer prompts data
    customer_prompts = get_customer_prompts()

    # Apply filter if a specific customer is selected
    if filter_customer != "All":
        selected_customer_id = filter_customer.split(" - ")[0]
        customer_prompts = customer_prompts[customer_prompts["customer_id"] == int(selected_customer_id)]

    # View customer prompts table
    st.header("Customer Prompts Table")
    st.dataframe(customer_prompts)

    # Dropdown for adding new prompts
    st.header("Add New Prompt")
    selected_customer = st.selectbox(
        "Select Customer by ID or Name",
        options=customers.to_dict("records"),
        format_func=lambda x: x["display"] if x else "Select a customer",
        key="add_prompt_customer_selector",
    )

    if selected_customer:
        st.write(f"Selected Customer ID: {selected_customer['customer_id']}")
        st.write(f"Selected Customer Name: {selected_customer['customer_name']}")

        # Input for OpenAI Prompt
        open_ai_prompt = st.text_area("Enter OpenAI Prompt", "")

        if st.button("Add to Customer Prompts"):
            if open_ai_prompt.strip():
                # Insert data into customer_prompts
                insert_query = """
                INSERT INTO customer_prompts (customer_id, open_ai_prompt)
                VALUES (%s, %s);
                """
                execute_query(insert_query, (selected_customer["customer_id"], open_ai_prompt))
                st.success("Prompt added successfully!")
            else:
                st.error("Prompt cannot be empty.")

    # Allow editing of prompts
    st.header("Edit Customer Prompt")
    selected_edit_customer = st.selectbox(
        "Select Customer by ID or Name to Edit",
        options=customers.to_dict("records"),
        format_func=lambda x: x["display"] if x else "Select a customer",
        key="edit_prompt_customer_selector",
    )

    if selected_edit_customer:
        st.write(f"Selected Customer ID: {selected_edit_customer['customer_id']}")
        st.write(f"Customer Name: {selected_edit_customer['customer_name']}")

        # Fetch prompts for the selected customer
        edit_customer_prompts = customer_prompts[customer_prompts["customer_id"] == selected_edit_customer["customer_id"]]

        if not edit_customer_prompts.empty:
            selected_prompt = st.selectbox(
                "Select a prompt to edit",
                options=edit_customer_prompts.to_dict("records"),
                format_func=lambda x: x["open_ai_prompt"] if x else "Select a prompt",
            )

            if selected_prompt:
                updated_prompt = st.text_area("Edit OpenAI Prompt", selected_prompt['open_ai_prompt'])

                if st.button("Update Prompt"):
                    update_query = """
                    UPDATE customer_prompts
                    SET open_ai_prompt = %s
                    WHERE customer_id = %s AND open_ai_prompt = %s;
                    """
                    execute_query(update_query, (updated_prompt, selected_prompt['customer_id'], selected_prompt['open_ai_prompt']))
                    st.success("Prompt updated successfully!")
        else:
            st.write("No prompts available for the selected customer.")

if __name__ == "__main__":
    main()
