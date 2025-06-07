import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

import streamlit as st
from sqlalchemy import create_engine

def get_engine():
    config = st.secrets["mysql"]
    connection_string = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(connection_string)


st.title("🔌 MySQL Cloud Connection Test")

try:
    engine = get_engine()
    df = pd.read_sql("SHOW TABLES", engine)
    st.success("Connected to MySQL Cloud DB ✅")
    st.dataframe(df)
except Exception as e:
    st.error(f"Connection failed ❌: {e}")
