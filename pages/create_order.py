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

# Function to connect to PostgreSQL and fetch data
def fetch_data_from_postgres(query):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

orders_query = "SELECT * FROM orders;"
orders_df = fetch_data_from_postgres(orders_query)

st.header("Orders Table")
if not orders_df.empty:
    st.dataframe(orders_df)
else:
    st.write("No data found in the 'orders' table.")

# Fetch customers and items from the database
customers_query = "SELECT * FROM customers;"
items_query = "SELECT * FROM items;"
customers_df = fetch_data_from_postgres(customers_query)
items_df = fetch_data_from_postgres(items_query)

# Initialize session state for the order cart and all orders
if "order_cart" not in st.session_state:
    st.session_state.order_cart = []

if "all_orders" not in st.session_state:
    st.session_state.all_orders = pd.DataFrame(
        columns=["OrderID", "CustomerID", "CustomerName", "ProductID", "ProductName", "Quantity", "SupplyDate"]
    )

def get_recommended_products(customer_id):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")

    # Fetch recent products ordered by the customer
    recent_orders_query = f"""
    SELECT DISTINCT product_id, MAX(supply_date) as last_order_date
    FROM orders
    WHERE customer_id = '{customer_id}'
    GROUP BY product_id
    ORDER BY last_order_date DESC
    LIMIT 5;  -- Limit to 5 most recent products
    """
    recent_products = pd.read_sql_query(recent_orders_query, conn)

    # Get product details for the recommended products
    if not recent_products.empty:
        recommended_products = items_df[items_df["product_id"].isin(recent_products["product_id"])].to_dict("records")
    else:
        recommended_products = []

    conn.close()

    # Add the "New Product" option
    recommended_products.append({"product_id": "NEW", "product_name": "New Product"})
    return recommended_products

# Page title
st.title("Order Entry System")

# Customer selection
st.header("Select Customer")
customer = st.selectbox(
    "Choose a customer",
    options=customers_df.to_dict("records"),
    format_func=lambda x: f"{x['customer_id']} - {x['customer_name']}"
)

# Product selection with recommendations
st.header("Select Product")
recommended_products = get_recommended_products(customer["customer_id"])

# Display recommended products
if recommended_products:
    st.subheader("Recommended Products (Including 'New Product')")
    product_selection = st.multiselect(
        "Choose a product",
        options=recommended_products,
        format_func=lambda x: f"{x['product_id']} - {x['product_name']}"
    )
else:
    st.write("No recommendations available.")
    product_selection = []

# Handle "New Product" selection
if any(prod["product_id"] == "NEW" for prod in product_selection):
    st.subheader("Select a New Product")
    all_product_selection = st.multiselect(
        "Choose from all products",
        options=items_df.to_dict("records"),
        format_func=lambda x: f"{x['product_id']} - {x['product_name']}"
    )
    # Add newly selected products to product_selection
    product_selection = [prod for prod in product_selection if prod["product_id"] != "NEW"]
    product_selection.extend(all_product_selection)

# Input fields for product
st.header("Product Details")
quantity = st.number_input("Enter quantity (applies to all selected products)", min_value=1, step=1)

# Add product(s) to order cart
if st.button("Add to Order"):
    if not product_selection:
        st.error("Please select at least one product to add to the order.")
    else:
        for selected_product in product_selection:
            product_entry = {
                "product_id": selected_product["product_id"],
                "product_name": selected_product["product_name"],
                "quantity": quantity,
            }
            st.session_state.order_cart.append(product_entry)
        st.success(f"Added {len(product_selection)} product(s) to the order.")

# Editable cart
if st.session_state.order_cart:
    st.header("Current Order Cart (Editable)")
    cart_data = st.session_state.order_cart.copy()
    updated_cart = []

    for i, product in enumerate(cart_data):
        col1, col2, col3, col4 = st.columns([3, 3, 2, 1])
        with col1:
            st.text(f"Product: {product['product_name']}")
        with col2:
            new_quantity = st.number_input(
                f"Quantity for {product['product_name']}",
                min_value=1,
                value=product["quantity"],
                key=f"quantity_{i}",
            )
        with col3:
            st.text(f"ID: {product['product_id']}")
        with col4:
            if st.button(f"Remove", key=f"remove_{i}"):
                continue  # Skip adding this product to the updated cart (deletes the row)

        # Add updated product to the new cart
        updated_cart.append(
            {
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "quantity": new_quantity,
            }
        )

    # Update the cart if changes were made
    st.session_state.order_cart = updated_cart
    st.success("Cart updated successfully!")

# Finalize and submit order
st.header("Finalize Order")
supply_date = st.date_input("Select supply date", value=date.today())

if st.button("Submit Order"):
    if not st.session_state.order_cart:
        st.error("Order cart is empty! Add products before submitting.")
    else:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        # Get the maximum current order ID
        # Get the maximum current order ID
        cur.execute("SELECT COALESCE(MAX(CAST(order_id AS INTEGER)), 0) FROM orders;")
        max_order_id = cur.fetchone()[0]
        order_id = max_order_id + 1


        # Create order DataFrame from the cart
        for item in st.session_state.order_cart:
            order_entry = {
                "order_id": order_id,
                "customer_name": str(customer["customer_name"]),  # Customer name
                "customer_id": str(customer["customer_id"]),  # Customer ID
                "product_id": str(item["product_id"]),       # Product ID
                "product_name": str(item["product_name"]),   # Product name
                "quantity": str(item["quantity"]),           # Quantity
                "supply_date": str(supply_date),             # Supply date
            }

            # Insert the order into the orders table
            insert_query = """
            INSERT INTO orders (order_id, customer_name, customer_id, product_id, product_name, quantity, supply_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            cur.execute(
                insert_query,
                (
                    order_entry["order_id"],
                    order_entry["customer_name"],
                    order_entry["customer_id"],
                    order_entry["product_id"],
                    order_entry["product_name"],
                    order_entry["quantity"],
                    order_entry["supply_date"],
                ),
            )

            # Append to session_state.all_orders for local display
            st.session_state.all_orders = pd.concat(
                [st.session_state.all_orders, pd.DataFrame([order_entry])], ignore_index=True
            )

        # Commit the transaction and close the connection
        conn.commit()
        cur.close()
        conn.close()

        # Reset order cart
        st.session_state.order_cart = []
        st.success(f"Order #{order_id} submitted successfully and saved to the database!")

# Generate XML
if st.button("Generate XML"):
    if st.session_state.all_orders.empty:
        st.error("No orders available to generate XML.")
    else:
        root = ET.Element("Orders")

        for _, row in st.session_state.all_orders.iterrows():
            item = ET.SubElement(root, "Item")
            ET.SubElement(item, "order_id").text = str(row["order_id"])
            ET.SubElement(item, "customer_id").text = str(row["customer_id"])
            ET.SubElement(item, "product_id").text = str(row["product_id"])
            ET.SubElement(item, "product_name").text = str(row["product_name"])
            ET.SubElement(item, "quantity").text = str(row["quantity"])
            ET.SubElement(item, "supply_date").text = str(row["supply_date"])
            ET.SubElement(item, "amount").text = "0"
            ET.SubElement(item, "doc_type").text = "11"

        xml_str = ET.tostring(root, encoding='unicode')

        with open("output.xml", "w", encoding="utf-8") as f:
            f.write(xml_str)

        st.success("XML file generated successfully: output.xml")
        st.code(xml_str, language="XML")