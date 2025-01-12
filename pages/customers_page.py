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

# Function to execute INSERT/DELETE queries
def execute_query(query, params=None):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

# Fetch customers table
query = """
    SELECT "ID", "customer_id", "customer_name", "SortGroup", "Address", 
           "City", "Zip", "Country", "Phone", "Fax"
    FROM customers;
"""
try:
    customers_df = fetch_data_from_postgres(query)
except Exception as e:
    st.error(f"An error occurred while fetching data: {e}")
    customers_df = pd.DataFrame()  # Empty DataFrame in case of error

# Streamlit Header
st.title("Customer Management App")
st.header("Customers Table")
if not customers_df.empty:
    st.dataframe(customers_df)
else:
    st.write("No data found in the 'customers' table.")

# Add Customer
st.subheader("Add Customer")
with st.form("add_customer_form"):
    ID = st.text_input("ID (Optional)")
    customer_id = st.text_input("Customer ID * (Required)")
    customer_name = st.text_input("Customer Name * (Required)")
    sort_group = st.text_input("Sort Group (Optional)")
    address = st.text_input("Address (Optional)")
    city = st.text_input("City (Optional)")
    zip_code = st.text_input("Zip (Optional)")
    country = st.text_input("Country (Optional)")
    phone = st.text_input("Phone (Optional)")
    fax = st.text_input("Fax (Optional)")
    submitted = st.form_submit_button("Add Customer")
    if submitted:
        # Validate required fields
        if customer_id and customer_name:
            add_query = """
                INSERT INTO customers (
                    "ID", "customer_id", "customer_name", "SortGroup", "Address", 
                    "City", "Zip", "Country", "Phone", "Fax"
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            params = (
                None if not ID else ID, customer_id, customer_name, sort_group or None, 
                address or None, city or None, zip_code or None, country or None, 
                phone or None, fax or None
            )
            execute_query(add_query, params)
            st.success(f"Customer {customer_name} added successfully!")
        else:
            st.warning("Please fill out the required fields: Customer ID and Customer Name.")

# Delete Customer
st.subheader("Delete Customer")
if not customers_df.empty:
    # Create a dropdown for selection
    customers_df['display_name'] = customers_df.apply(
        lambda x: f"{x['customer_id']} - {x['customer_name']}", axis=1
    )
    selected_customer = st.selectbox(
        "Select a customer to delete:",
        customers_df.to_dict('records'),
        format_func=lambda x: x['display_name']
    )

    # Delete button
    if st.button("Delete Customer"):
        delete_query = "DELETE FROM customers WHERE customer_id = %s;"
        execute_query(delete_query, (selected_customer['customer_id'],))
        st.success(f"Customer {selected_customer['display_name']} deleted successfully!")
        
        # Refresh the page by clearing session state and using query parameters
        for key in st.session_state.keys():
            del st.session_state[key]
        st.query_params.update(refresh="true")
        st.stop()  # Stop further execution to simulate a refresh
else:
    st.write("No customers available for deletion.")

# Refresh Customers Table
if st.button("Refresh Data"):
    try:
        customers_df = fetch_data_from_postgres(query)
        if not customers_df.empty:
            st.dataframe(customers_df)
        else:
            st.write("No data found in the 'customers' table.")
    except Exception as e:
        st.error(f"An error occurred while refreshing data: {e}")
