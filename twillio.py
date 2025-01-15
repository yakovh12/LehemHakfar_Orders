import os
from flask import Flask, request, render_template, redirect, url_for, flash
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from openai import OpenAI
import psycopg2
import pandas as pd
from datetime import date, datetime, timedelta
import logging  
# Load environment variables from .env file

load_dotenv(override=True)


# Initialize Flask app
app = Flask(__name__)
TWILIO_API_KEY = os.getenv("TWILIO_API_KEY")
TWILIO_ACCOUNT = os.getenv("TWILIO_ACCOUNT")
twillio_client = Client(TWILIO_ACCOUNT, TWILIO_API_KEY)
DATABASE_URL = os.environ.get("DATABASE_URL")
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
    response = openai.chat.completions.create(model="gpt-4",
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


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_order():
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        flash("OPENAI_API_KEY is not set. Please check your .env file.")
        return redirect(url_for('home'))

    openai.api_key = openai_api_key

    # Log or print request.form for debugging purposes
    logging.debug(f"Received form data: {request.form}")
    print(request.form)  # This will now work because it's inside a request context.

    user_input = request.form.get('user_input')
    if not user_input:
        flash("Input is required.")
        return redirect(url_for('home'))

    customer_key = get_customer_from_input(openai, user_input)

    if customer_key == "unknown":
        flash("Unable to determine the customer from the provided input.")
        return redirect(url_for('home'))

    try:
        response = parse_order(openai, customer_key, user_input)
        flash(f"Data successfully written to Google Sheets! Updated {response} cells.")
    except ValueError as e:
        flash(f"Error processing AI response: {e}")
    except Exception as e:
        flash(f"Unexpected error: {e}")
    
    return redirect(url_for('home'))

@app.route('/twilio-webhook', methods=['POST'])
def twilio_webhook():
    logging.debug(f"Twilio webhook data: {request.form}")
    print(request.form)  # Works here because it's inside a route.

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return "OPENAI_API_KEY not set", 500

    openai.api_key = openai_api_key

    user_input = request.form.get('Body')  # WhatsApp message content
    from_number = request.form.get('From')  # Sender's phone number

    if not user_input:
        return "No input provided", 400

    customer_key = get_customer_from_input(openai, user_input)

    if customer_key == "unknown":
        resp = MessagingResponse()
        resp.message("Sorry, we couldn't determine the customer from your input.")
        return str(resp)

    try:
        response = parse_order(openai, customer_key, user_input)
        resp = MessagingResponse()
        resp.message(f"Order processed successfully! Updated {response} cells.")
        return str(resp)
    except ValueError as e:
        resp = MessagingResponse()
        resp.message(f"Error processing your request: {e}")
        return str(resp)
    except Exception as e:
        resp = MessagingResponse()
        resp.message(f"Unexpected error: {e}")
        return str(resp)
    
if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

