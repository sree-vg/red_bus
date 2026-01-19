import streamlit as st
import pymysql
from pymysql import Error
import pandas as pd
import numpy as np
import time
import qrcode
from PIL import Image
import io

# Function to handle timedelta to HH:MM format conversion
def timedelta_to_hhmm(value):
    t_seconds = value.seconds
    hours = t_seconds // 3600  # 1 hour = 3600 seconds
    minutes = (t_seconds % 3600) // 60  # 1 hour = 60 minutes
    return f"{hours:02}:{minutes:02}"  # Formatting to 00:00

# Function to configure database connection
def configuration():
    try:
        connection = pymysql.connect(
            host='localhost', user='root', password='09876', database='red_bus')
        print("Connection successful")
        return connection
    except Error as e:
        print("Error occurred during configuration:", e)

# Function to connect to the MySQL database
def connect():
    try:
        conn = configuration()
        if conn is None:
            st.error("❌ Database connection failed")
            return None
        if conn.open:
            print("Connection completed")
        return conn
    except Error as e:
        st.error(f"Database error: {e}")
        return None

# Function to fetch distinct values (like state names)
def fetch_distinct_value(conn, query_distinct):
    with conn.cursor() as c:
        try:
            c.execute(query_distinct)
            result = [row[0] for row in c.fetchall()]
            print("Fetched distinct values")
            return result
        except Error as e:
            print("Error occurred when fetching distinct values:", e)

# Function to fetch route names based on the state
def fetch_route_names(conn, query_routes_names):
    with conn.cursor() as c:
        try:
            c.execute(query_routes_names)
            result = [row[0] for row in c.fetchall()]
            print("Fetched route names")
            return result
        except Error as e:
            print("Error occurred when fetching route names:", e)

# Function to fetch filtered data based on user input
def fetch_filtered_value(conn, query_filtered_value):
    with conn.cursor() as c:
        try:
            c.execute(query_filtered_value)
            columns = [desc[0] for desc in c.description]
            data = c.fetchall()
            df = pd.DataFrame(data, columns=columns, index=[index + 1 for index in range(len(data))])

            # Apply formatting if columns exist
            if "departing_time" in df.columns:
                df["departing_time"] = df["departing_time"].apply(timedelta_to_hhmm)
            if "reaching_time" in df.columns:
                df["reaching_time"] = df["reaching_time"].apply(timedelta_to_hhmm)
            if "star_rating" in df.columns:
                df['star_rating'] = df['star_rating'].replace(0.0, np.nan)
            return df
        except Error as e:
            print("Error occurred when fetching filtered data:", e)
            return pd.DataFrame()

# Close the database connection
def close_connection(conn):
    if conn:
        try:
            conn.close()
            print("Connection closed successfully")
        except Error as e:
            print("Error occurred when closing the connection:", e)

# Connect to the database
conn = connect()

# Setting page configuration for Streamlit
st.set_page_config(
    page_title="Redbus - Search and Book Your Bus 🚌",
    page_icon=":oncoming_bus:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar Navigation
with st.sidebar:
    st.title("Redbus")
    st.markdown("Book Your Ride 🚌")
    if st.button("Home"):
        st.session_state.page = "home"
    if st.button("Search Buses"):
        st.session_state.page = "search"

# Initialize state if not already set
if "page" not in st.session_state:
    st.session_state.page = "home"

# Home Page
if st.session_state.page == "home":
    st.title(":red[REDBUS] - Your ticket to less stress 🚌")
    st.markdown(""" 
    Redbus is an online bus ticketing platform founded in 2006 in India. 
    It allows users to book bus tickets through its website and mobile app, 
    providing access to a wide network of bus operators across various routes. 
    """)
    st.image(
        "https://akm-img-a-in.tosshub.com/indiatoday/images/story/202204/redbus_1200x768.png?VersionId=JXyxPyUZzox7t3MdV6IBbiu1NbhivRvE&size=690:388", 
        caption="Redbus Booking", 
        use_container_width=True
    )

# Search Buses Page
elif st.session_state.page == "search":
    st.title(":red[REDBUS] - 🔍 Search Bus")
    
    route_name = '--- Select Route ---'   # ✅ IMPORTANT FIX

    col1, col2 = st.columns([4, 1])

    with col1:
        state_query = "SELECT DISTINCT state_name FROM route_data;"
        state_names = fetch_distinct_value(conn, state_query)
        state_name = st.selectbox("State", ['--- Select State ---'] + state_names)

        if state_name != '--- Select State ---':
            route_query = f"""
                SELECT route_name 
                FROM route_data 
                WHERE state_name = '{state_name}';
            """
            route_names = fetch_route_names(conn, route_query)
            route_name = st.selectbox("Route", ['--- Select Route ---'] + route_names)

    with col2:
        bus_types_query = "SELECT DISTINCT bus_type FROM bus_data;"
        bus_types = fetch_distinct_value(conn, bus_types_query)
        bus_type = st.selectbox("Bus Type", ['All'] + bus_types)

        price_range = st.slider("Price Range", 0, 3000, (0, 3000), 100)
        min_price, max_price = price_range

        rating = st.slider("Star Rating", 0, 5, (0, 5), 1)
        min_rating, max_rating = rating

    # ✅ VALIDATION
    if state_name == '--- Select State ---' or route_name == '--- Select Route ---':
        st.warning("⚠️ Please select State and Route")
        st.stop()

    if st.button("Search"):
        query = f"""
        SELECT r.route_name, r.route_link, b.bus_name, b.bus_type, b.departing_time, 
               b.duration, b.reaching_time, b.star_rating, b.price, b.seat_available
        FROM route_data r
        JOIN bus_data b ON r.route_no = b.bus_no
        WHERE r.state_name = '{state_name}' 
          AND r.route_name = '{route_name}' 
          AND (b.bus_type = '{bus_type}' OR '{bus_type}' = 'All') 
          AND b.star_rating BETWEEN {min_rating} AND {max_rating}
          AND b.price BETWEEN {min_price} AND {max_price};
        """

        with st.spinner('Searching...'):
            time.sleep(2)
            filtered_data = fetch_filtered_value(conn, query)

        if not filtered_data.empty:
            st.dataframe(filtered_data)
        else:
            st.markdown("<h4>Sorry, no buses found for the selected filters</h4>", unsafe_allow_html=True)


# Close the database connection at the end
close_connection(conn)
