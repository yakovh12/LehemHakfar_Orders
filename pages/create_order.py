import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import xml.etree.ElementTree as ET
from openai import OpenAI
import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()

query_params = st.query_params

# PostgreSQL database connection details
DATABASE_URL = os.environ.get("DATABASE_URL")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Function to connect to PostgreSQL and fetch data
def fetch_data_from_postgres(query):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_customer_from_input(client, user_input):
    customers_query = "SELECT customer_id, customer_name FROM customers;"
    customers_df = fetch_data_from_postgres(customers_query)    
    customer_json = customers_df.to_dict('records')
    prompt = f"""
    You are a supervisor of AI agents. Your mission is to understand from the user input which company it is related to 
    and to send it to the correct AI agent expert. You do this by returning only the exact customer_id as number from the following list:
    {customer_json}
    If you are unsure or can't determine the company, respond with "unknown".
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # Generate the response from OpenAI
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input},
        ]
    )

    # Return the AI's response
    return completion.choices[0].message.content.strip()

def get_customer_prompt(customer_id):
    query = f"""
    SELECT open_ai_prompt
    FROM customer_prompts
    WHERE customer_id = '{customer_id}';
    """
    # Fetch the data as a DataFrame
    result = fetch_data_from_postgres(query)
    
    # Extract the value from the DataFrame if it exists
    if not result.empty and 'open_ai_prompt' in result.columns:
        return result['open_ai_prompt'].iloc[0]  # Get the first value in the 'open_ai_prompt' column
    else:
        return None  # Return None if no results are found


def get_next_weekday(weekday_name):
    """Get the next occurrence of the specified weekday."""
    today = datetime.now()
    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    target_day = days_of_week.index(weekday_name.lower())
    days_ahead = (target_day - today.weekday() + 7) % 7
    return today + timedelta(days=days_ahead if days_ahead > 0 else 7)

def parse_order(input_text, customer_id, customer_prompts):
    """Parse the order using OpenAI chat completion."""
    today_date = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")

    # Construct the prompt
    system_prompt = f"""
    you are AI agent that processes orders. you mission is receive order as it sent from the customer and to parse it to a valid JSON structure.
    There are general instructions that you should follow:
    1. Supply Date: If a date is mentioned, use it. If a day is mentioned (e.g., Monday), calculate the next occurrence of that day. If no date is provided, use today’s date which is {today_date}
    2. Customer ID: {customer_id}
    3. Customer Name: it doesnt matter what you return because we map the customer_id to the customer_name.
    3. Product ID: you will receive it in specific instcructions.
    4. Product Name: it doesnt matter what you return because we map the product_id to the product_name.
    5. Quantity: you will receive it in specific instructions.
    6. order_id: it doesnt matter what you return because we map the product id to the product name.
    
    Output JSON Example:
    3. Example output for multiple products:
[
    {{
        "order_id": "1",
        "customer_name": "Customer A",
        "customer_id": "1001",
        "product_id": "2001",
        "product_name": "Bread",
        "quantity": 400,
        "supply_date": "2025-01-16"
    }},
    {{
        "order_id": "2",
        "customer_name": "Customer A",
        "customer_id": "1001",
        "product_id": "2002",
        "product_name": "Roll",
        "quantity": 80,
        "supply_date": "2025-01-16"
    }}
]
    """
    # Call OpenAI API
    response = client.chat.completions.create(model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content":f"specific instruction: {customer_prompts}"},
        {"role": "assistant", "content": "OK"},
        {"role": "user", "content":f"user input:{input_text}"}
    ]
    ,temperature=0.0
    )

    # Extract and return the response
    return response.choices[0].message.content


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
        columns=["OrderID", "CustomerID", "CustomerName", "ProductID", "ProductName", "Quantity", "SupplyDate", "CreatedAt"]
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
    LIMIT 5;
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
                "created_at": datetime.now().isoformat(),    # Current timestamp
            }

            # Insert the order into the orders table
            insert_query = """
            INSERT INTO orders (order_id, customer_name, customer_id, product_id, product_name, quantity, supply_date, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
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
                    order_entry["created_at"],
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

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

st.header("AI Assistant")
order_input = st.text_area("Enter the customer order prompt:")

# Temporary storage for the parsed data
if "parsed_df" not in st.session_state:
    st.session_state.parsed_df = None

if st.button("Process Prompt"):
    if order_input.strip():
        try:
            customer_id = get_customer_from_input(client, order_input)
            st.write(f"Customer ID: {customer_id}")
            if customer_id == "unknown":
                raise ValueError("Customer ID could not be determined.")


            customer_prompts = get_customer_prompt(customer_id)
            st.write(f"Customer Prompts: {customer_prompts}")

            

            # Simulate `parse_order` response for demonstration
            result = parse_order(order_input, customer_id, customer_prompts)
            result = json.loads(result)

            st.write(result)
        
            # Parse the AI response
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    st.error("The result is not a valid JSON structure.")
                    raise

            st.success("Prompt processed successfully!")
            st.json(result)

            # Flatten the dictionary and convert to DataFrame
            if isinstance(result, list):  # Handle multiple products
                flattened_results = [flatten_dict(item) for item in result]  # Flatten each dictionary
                df = pd.DataFrame(flattened_results)  # Create DataFrame from the list of flattened dictionaries
            elif isinstance(result, dict):  # Handle a single product
                flattened_result = flatten_dict(result)
                df = pd.DataFrame([flattened_result])  # Create DataFrame with one row
            else:
                raise ValueError("Unexpected response format. Expected a dictionary or list of dictionaries.")

            # Format dates
            if "supply_date" in df.columns:
                df["supply_date"] = pd.to_datetime(df["supply_date"]).dt.strftime('%Y-%m-%d')
            df["created_at"] = datetime.now().isoformat()

            # Convert necessary fields to strings
            df["product_id"] = df["product_id"].astype(str)
            df["customer_id"] = df["customer_id"].astype(str)

            # Map customer_name and product_name from external DataFrames
            df["customer_name"] = df["customer_id"].map(lambda x: customers_df[customers_df["customer_id"] == x]["customer_name"].values[0])
            df["product_name"] = df["product_id"].map(lambda x: items_df[items_df["product_id"] == x]["product_name"].values[0])

            # Generate unique order IDs
            conn = psycopg2.connect(DATABASE_URL, sslmode="require")
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(MAX(CAST(order_id AS INTEGER)), 0) FROM orders;")
            max_order_id = cur.fetchone()[0]

            # Assign unique order_id for each row
            df["order_id"] = max_order_id + 1
            df["order_id"] = df["order_id"].astype(str)

            # Close the database connection
            conn.close()

            # Save the DataFrame to session state for review
            st.session_state.parsed_df = df
            st.success("Data parsed successfully! Review the data below before submitting.")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
    else:
        st.warning("Please enter a valid order prompt.")

# Review the parsed data
if st.session_state.parsed_df is not None:
    st.header("Review Data")
    st.write("Review the parsed data below before submitting it to the database.")
    st.dataframe(st.session_state.parsed_df)

    # Button to push data to SQL table
    if st.button("Push to SQL Table"):
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode="require")
            cur = conn.cursor()

            for _, row in st.session_state.parsed_df.iterrows():
                insert_query = """
                INSERT INTO orders (order_id, customer_name, customer_id, product_id, product_name, quantity, supply_date, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """
                cur.execute(insert_query, tuple(row))

            conn.commit()
            st.success("Data has been successfully pushed to the orders table.")

            # Clear the session state after successful push
            st.session_state.parsed_df = None

        except Exception as db_error:
            st.error(f"An error occurred while inserting data into the database: {db_error}")
        finally:
            cur.close()
            conn.close()
