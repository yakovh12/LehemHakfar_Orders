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

# Fetch items table
query = """
    SELECT "ID", "product_id", "product_name", "ForignName", "SortGroup", 
           "Filter", "Price", "Currency", "PurchPrice", "PurchCurrency"
    FROM items;
"""
try:
    items_df = fetch_data_from_postgres(query)
except Exception as e:
    st.error(f"An error occurred while fetching data: {e}")
    items_df = pd.DataFrame()  # Empty DataFrame in case of error

# Streamlit Header
st.title("Product Management App")
st.header("Items Table")
if not items_df.empty:
    st.dataframe(items_df)
else:
    st.write("No data found in the 'items' table.")

# Add Product
st.subheader("Add Product")
with st.form("add_product_form"):
    product_id = st.text_input("Product ID * (Required)")
    product_name = st.text_input("Product Name * (Required)")
    forign_name = st.text_input("Foreign Name (Optional)")
    sort_group = st.text_input("Sort Group (Optional)")
    filter_column = st.text_input("Filter (Optional)")
    price = st.number_input("Price (Optional)", min_value=0.0, step=0.01, value=0.0)
    currency = st.text_input("Currency (Optional)")
    purch_price = st.number_input("Purchase Price (Optional)", min_value=0.0, step=0.01, value=0.0)
    purch_currency = st.text_input("Purchase Currency (Optional)")
    submitted = st.form_submit_button("Add Product")
    if submitted:
        # Validate required fields
        if product_id and product_name:
            add_query = """
                INSERT INTO items (
                    "ID", "product_id", "product_name", "ForignName", "SortGroup", 
                    "Filter", "Price", "Currency", "PurchPrice", "PurchCurrency"
                )
                VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            params = (
                product_id,
                product_name,
                forign_name or None,  # Replace empty optional fields with None
                sort_group or None,
                filter_column or None,
                price or None,
                currency or None,
                purch_price or None,
                purch_currency or None,
            )
            execute_query(add_query, params)
            st.success(f"Product '{product_name}' added successfully!")
        else:
            st.warning("Please fill out the required fields: Product ID and Product Name.")

# Delete Product
st.subheader("Delete Product")
if not items_df.empty:
    # Create a dropdown for selection
    items_df['display_name'] = items_df.apply(
        lambda x: f"{x['product_id']} - {x['product_name']}", axis=1
    )
    selected_product = st.selectbox(
        "Select a product to delete:",
        items_df.to_dict('records'),
        format_func=lambda x: x['display_name']
    )

    # Delete button
    if st.button("Delete Product"):
        delete_query = "DELETE FROM items WHERE product_id = %s;"
        execute_query(delete_query, (selected_product['product_id'],))
        st.success(f"Product {selected_product['display_name']} deleted successfully!")

        # Clear session state and refresh
        for key in st.session_state.keys():
            del st.session_state[key]
        st.query_params.update(refresh="true")
        st.stop()
else:
    st.write("No products available for deletion.")

# Refresh Items Table
if st.button("Refresh Data"):
    try:
        items_df = fetch_data_from_postgres(query)
        if not items_df.empty:
            st.dataframe(items_df)
        else:
            st.write("No data found in the 'items' table.")
    except Exception as e:
        st.error(f"An error occurred while refreshing data: {e}")
