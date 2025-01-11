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
    created_at_start = st.date_input("Created At - Start Date", value=None)
    created_at_end = st.date_input("Created At - End Date", value=None)

    filtered_df = orders_df.copy()

    if customer_filter:
        filtered_df = filtered_df[filtered_df["customer_name"].str.contains(customer_filter, case=False, na=False)]

    if date_filter:
        # Convert both supply_date and date_filter to the same format
        filtered_df["supply_date"] = pd.to_datetime(filtered_df["supply_date"]).dt.date
        filtered_df = filtered_df[filtered_df["supply_date"] == date_filter]

    # Apply created_at date range filter
    if created_at_start or created_at_end:
        filtered_df["created_at"] = pd.to_datetime(filtered_df["created_at"])
        if created_at_start:
            filtered_df = filtered_df[filtered_df["created_at"] >= pd.to_datetime(created_at_start)]
        if created_at_end:
            filtered_df = filtered_df[filtered_df["created_at"] <= pd.to_datetime(created_at_end)]

    # Add 'doctype' column
    filtered_df["doctype"] = 11

    st.write(f"Filtered {len(filtered_df)} rows.")
    st.dataframe(filtered_df)

    # Export options
    st.subheader("Export Data")

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
