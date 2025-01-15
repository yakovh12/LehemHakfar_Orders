import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO

# Streamlit app
st.title("POS Excel to XML")

# File uploader and user input
user_input = st.text_input("Enter a reference number:")
uploaded_file = st.file_uploader("Upload an Excel file", type="xlsx")

if uploaded_file:
    # Load the Excel into a DataFrame
    df = pd.read_excel(uploaded_file)

    # Ensure the DataFrame has the expected structure before renaming columns
    if len(df.columns) >= 43:  # Ensure at least 43 columns for your schema
        df.columns = [
            "z_number", "register_number", "date", "first_sale_date", "credit_card",
            "credit_counter", "cash", "cash_counter", "purchase_voucher", "purchase_voucher_counter",
            "credit_voucher", "credit_voucher_counter", "checks", "checks_counter", "change_in_credit_voucher",
            "credit_voucher_change_counter", "credit_sales_delivery_notes", "credit_sales_tax_invoices",
            "credit_sales_total", "positive_card_loading", "positive_card_loading_counter",
            "payment_with_positive_card", "total_ten_bis", "total_plexi", "total_goody", "total_dts",
            "total_kashcash", "total_mishlocha", "total_mishlocha_cash", "total_payit", "total_yad_sarig",
            "total_internet_payments", "payment_with_positive_card_tms", "notes_quantity", "total_receipts",
            "coin_rounding", "total_sales_including_vat", "total_sales_excluding_vat", "isracard", "visa_cal",
            "american_express", "leumicard", "diners"
        ]

        # Remove the first and last rows
        df = df.iloc[1:-1]  # Remove the first and last rows

        # Create the new DataFrame
        new_df = pd.DataFrame({
            "reference": user_input,  # Use user input
            "account_id": "50009",
            "item_id": "11000",
            "item_name": df["z_number"],
            "quantity": 1,
            "amount": df["total_sales_excluding_vat"],
            "doc_type": "87"
        })

        # Display the new DataFrame
        st.write("### Transformed DataFrame:")
        st.dataframe(new_df)

        # Create XML structure
        root = ET.Element("Data")
        for _, row in new_df.iterrows():
            item = ET.SubElement(root, "Item")

            reference = ET.SubElement(item, "Reference")
            reference.text = str(row["reference"])

            account_id = ET.SubElement(item, "AccountID")
            account_id.text = str(row["account_id"])

            item_id = ET.SubElement(item, "ItemID")
            item_id.text = str(row["item_id"])

            item_name = ET.SubElement(item, "ItemName")
            item_name.text = str(row["item_name"])

            quantity = ET.SubElement(item, "Quantity")
            quantity.text = str(row["quantity"])

            amount = ET.SubElement(item, "Amount")
            amount.text = str(row["amount"])

            doc_type = ET.SubElement(item, "DocType")
            doc_type.text = str(row["doc_type"])

        # Convert XML tree to string
        xml_str = ET.tostring(root, encoding='unicode')

        # Download the XML file
        st.write("### Download the XML File:")
        xml_file = BytesIO()
        xml_file.write(xml_str.encode('utf-8'))
        xml_file.seek(0)

        st.download_button(
            label="Download XML",
            data=xml_file,
            file_name="output.xml",
            mime="application/xml"
        )

        st.success("XML file created successfully!")
    else:
        st.error("The uploaded Excel file does not have the required structure or enough columns.")
