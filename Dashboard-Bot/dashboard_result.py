import streamlit as st
import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection details
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Function to connect to the database
def get_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
        return None

# Function to fetch data from the database
@st.cache_data
def fetch_data():
    conn = get_connection()
    if conn is not None:
        query = "SELECT FIELD_NAME, FIELD_VALUE FROM obj_motorinsurance_data_178"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    else:
        return pd.DataFrame()

# Function to process the data
def process_data(df):
    # Filter for fuel data
    fuel_data = df[df['FIELD_NAME'] == 'fuel']

    # Count occurrences of each fuel type
    fuel_counts = fuel_data['FIELD_VALUE'].value_counts().reset_index()
    fuel_counts.columns = ['Fuel Type', 'Number of Users']
    return fuel_counts

# Streamlit app layout
st.title("Motor Insurance Dashboard")
st.subheader("Fuel Type Usage Analysis")

# Fetch and process data
with st.spinner("Loading data..."):
    data = fetch_data()
    if data.empty:
        st.error("No data found.")
    else:
        fuel_usage = process_data(data)
        st.success("Data loaded successfully!")

# Display the fuel usage table
if not fuel_usage.empty:
    st.subheader("Number of Users by Fuel Type")
    st.dataframe(fuel_usage)

# Add download functionality
csv = fuel_usage.to_csv(index=False)
st.download_button(
    label="Download Fuel Usage Data as CSV",
    data=csv,
    file_name='fuel_usage_data.csv',
    mime='text/csv'
)

# Footer
st.markdown("---")
st.write("Data Source: Motor Insurance Database")