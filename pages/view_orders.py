import streamlit as st
import pandas as pd
from datetime import date
import xml.etree.ElementTree as ET
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

# PostgreSQL database connection details
DATABASE_URL = os.environ.get("DATABASE_URL")

def convert_to_csv(df):
    # Use utf-8-sig encoding for Hebrew support in CSV
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

def convert_to_xml(df):
    root = ET.Element("Orders")
    for _, row in df.iterrows():
        item = ET.SubElement(root, "Item")
        for col in df.columns:
            ET.SubElement(item, col).text = str(row[col])
    return ET.tostring(root, encoding="utf-8").decode("utf-8")

# Function to connect to PostgreSQL and fetch data
def fetch_data_from_postgres(query):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def generate_html(df):
    grouped = df.groupby("customer_name")
    supply_date = df["supply_date"].iloc[0]
    html_content = f"""
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>תמצית הזמנות</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                direction: rtl;
            }}
            .container {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 20px;
                page-break-inside: avoid;
            }}
            .column {{
                border: 1px solid #ddd;
                padding: 10px;
                box-sizing: border-box;
                page-break-inside: avoid;
            }}
            .order {{
                margin-bottom: 15px;
            }}
            .order-title {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
                direction: rtl;
                unicode-bidi: isolate;
            }}
            .product {{
                font-size: 18px;
                margin-bottom: 5px;
                direction: rtl;
                unicode-bidi: isolate;
            }}
        </style>
    </head>
    <body>
        <h1 style="text-align: center;">הזמנות לתאריך: {supply_date} </h1>
        <div class="container">
    """
    for customer_name, group in grouped:
        reshaped_order_id = f"שם לקוח: {customer_name}"
        order_html = f"""
        <div class="order">
            <div class="order-title">{reshaped_order_id}</div>
        """
        for _, row in group.iterrows():
            product_id = row.get("product_id", "Unknown Product ID")
            product_name = row.get("product_name", "Unknown Product")
            quantity = str(row.get("quantity", "Unknown Quantity"))
            order_html += f"""
            <div class="product">{product_id} {product_name}: {quantity}</div>
            """
        order_html += "</div>"
        html_content += f'<div class="column">{order_html}</div>'
    html_content += """
        </div>
    </body>
    </html>
    """
    return html_content

def data_exploration_page():
    st.title("Data Exploration and Export")

    # Fetch orders data
    orders_query = "SELECT * FROM orders;"
    orders_df = fetch_data_from_postgres(orders_query)

    if orders_df.empty:
        st.write("No data available to display.")
        return

    # Display the dataframe
    st.header("Orders Data")
    st.dataframe(orders_df)

    # Filtering options
    st.subheader("Filter Data")
    customer_filter = st.text_input("Filter by Customer Name (contains)")
    date_filter = st.date_input("Filter by Supply Date", value=None)

    created_at_start = st.text_input("Created At - Start Timestamp (YYYY-MM-DD HH:MM:SS)", value=None)
    created_at_end = st.text_input("Created At - End Timestamp (YYYY-MM-DD HH:MM:SS)", value=None)

    filtered_df = orders_df.copy()

    if customer_filter:
        filtered_df = filtered_df[filtered_df["customer_name"].str.contains(customer_filter, case=False, na=False)]

    if date_filter:
        # Convert both supply_date and date_filter to the same format
        filtered_df["supply_date"] = pd.to_datetime(filtered_df["supply_date"]).dt.date
        filtered_df = filtered_df[filtered_df["supply_date"] == date_filter]

    if created_at_start or created_at_end:
        filtered_df["created_at"] = pd.to_datetime(filtered_df["created_at"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        
        if created_at_start:
            start_timestamp = pd.to_datetime(created_at_start)
            filtered_df = filtered_df[filtered_df["created_at"] >= start_timestamp]

        if created_at_end:
            end_timestamp = pd.to_datetime(created_at_end)
            filtered_df = filtered_df[filtered_df["created_at"] <= end_timestamp]

    # Add 'doctype' column
    filtered_df["doctype"] = 11

    st.write(f"Filtered {len(filtered_df)} rows.")
    st.dataframe(filtered_df)

    # New Section: Sum by Product ID and Product Name
    st.subheader("Sum by Product")
    if "quantity" in filtered_df.columns:
        sum_by_product = (
            filtered_df.groupby(["product_id", "product_name"])["quantity"]
            .sum()
            .reset_index()
            .sort_values(by="quantity", ascending=False)
        )
        st.dataframe(sum_by_product)

        # Export the aggregated data
        sum_csv_data = convert_to_csv(sum_by_product)
        st.download_button(
            label="Download Sum by Product as CSV",
            data=sum_csv_data,
            file_name="sum_by_product.csv",
            mime="text/csv",
        )
    else:
        st.write("The 'quantity' column is missing. Unable to calculate sum by product.")

    # Export options
    st.subheader("Export Data")

    csv_data = convert_to_csv(filtered_df)
    xml_data = convert_to_xml(filtered_df)
    html_data = generate_html(filtered_df)

    st.download_button(
        label="Download as CSV",
        data=csv_data,
        file_name="filtered_orders.csv",
        mime="text/csv",
    )

    st.download_button(
        label="Download as XML",
        data=xml_data,
        file_name="filtered_orders.xml",
        mime="application/xml",
    )

    st.download_button(
        label="Download as HTML",
        data=html_data,
        file_name="filtered_orders.html",
        mime="text/html",
    )

# Directly call the data exploration page
data_exploration_page()
