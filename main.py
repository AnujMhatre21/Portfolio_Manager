
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from yahooquery import search, Ticker
import mysql.connector
import yfinance as yf
import base64
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from portfolio.stocks.portfolioDashBoard import portfolioDashBoardClass
from portfolio.stocks.treeMap import treeMap


# --- DB Connection ---

# def get_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="root",
#         database="microservices"
#     )

# SQLAlchemy connection string
def get_engine():
    config = st.secrets["mysql"]
    connection_string = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(connection_string)


# --- Streamlit App ---
st.set_page_config("💰 Financial Planner", layout="wide")
st.title("💼 One-Stop Financial Planner")

menu = st.sidebar.selectbox(
    "🔎 Navigate", ["Portfolio", "Overview", "Credit Cards", "Goals", "GPT Advisor"])

if menu == "Portfolio":

    # st.subheader("📈 Portfolio")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["💼 Holdings Overview",  "📈 Stocks", "Mutual Fund", "Gold", "Cash"])
    # --- Tab 1: Holdings Overview ---
    with tab1:
        st.markdown("### 🧾 Portfolio Overview")

    with tab2:
        # count = st_autorefresh(interval=20000, key="portfolio_autorefresh")
        # st.write(f"Auto-refresh count: {count}")

        portfoliodashboard = portfolioDashBoardClass()
        df = portfoliodashboard.render()
        # print(df)
        treeMap().render(df)


    with tab3:
        st.markdown("### 📊 Mutual Fund Holdings")
        st.info("This feature is under development. Stay tuned!")

    with tab4:
        st.markdown("### 📊 Gold Holdings")
        st.info("This feature is under development. Stay tuned!")

    with tab5:
        st.markdown("### 💵 Cash Holdings")
        st.info("This feature is under development. Stay tuned!")

    # with tab5:
    #     import streamlit as st
    #     # Example values

    #     st.markdown("### 💵 Cash Holdings")
    #     conn = engine.raw_connection()
    #     df = pd.read_sql("SELECT * FROM cash_holdings", con=engine)
    #     conn.close()

    #     if df.empty:
    #         st.info("No cash holdings added yet.")
    #     else:
    #         st.dataframe(df)

    #     with st.form("cash_form", clear_on_submit=False):
    #         amount = st.number_input("Amount", 0)
    #         description = st.text_input("Description")
    #         if st.form_submit_button("Add Cash"):
    #             conn = engine.raw_connection()
    #             cur = conn.cursor()
    #             cur.execute(
    #                 "INSERT INTO cash_holdings (amount, description) VALUES (%s, %s)", (amount, description))
    #             conn.commit()
    #             conn.close()
    #             st.success("Cash added successfully!")

elif menu == "Overview":
    st.subheader("📊 Financial Overview")
    st.markdown("### 🏦 Bank Accounts")
    st.info("This feature is under development. Stay tuned!")

    st.markdown("### 💳 Credit Cards")
    st.info("This feature is under development. Stay tuned!")

    st.markdown("### 🏠 Loans")
    st.info("This feature is under development. Stay tuned!")

elif menu == "Credit Cards":
    st.subheader("💳 Credit Cards")
    st.info("This feature is under development. Stay tuned!")

elif menu == "Goals":
    st.subheader("🎯 Financial Goals")
    st.info("This feature is under development. Stay tuned!")

elif menu == "GPT Advisor":
    st.subheader("🤖 GPT Financial Advisor")
    st.info("This feature is under development. Stay tuned!")
    # Add your GPT integration here
    # For example, you can use OpenAI's API to get financial advice
    # or answer user queries related to finance.
