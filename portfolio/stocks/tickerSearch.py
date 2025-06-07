import pandas as pd
import requests
from difflib import get_close_matches
import streamlit as st

INSTRUMENTS_URL = "https://api.kite.trade/instruments"
LOCAL_FILE = "kite_instruments.csv"

@st.cache_data(ttl=86400, show_spinner=False)
def download_kite_instruments():
    """Downloads and caches the latest instrument list from Kite (Zerodha)."""
    try:
        response = requests.get(INSTRUMENTS_URL)
        response.raise_for_status()

        with open(LOCAL_FILE, "wb") as f:
            f.write(response.content)

        df = pd.read_csv(LOCAL_FILE)
        return df
    except Exception as e:
        st.error(f"Failed to download instruments list: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def search_ticker_symbols(query: str, max_results: int = 10):
    """
    Searches for ticker symbols in the NSE instrument list from Kite.
    Returns a list of matching tradingsymbols and company names.
    """
    instruments_df = download_kite_instruments()
    if instruments_df.empty:
        return []

    # Filter only NSE equity instruments
    nse_df = instruments_df[
        (instruments_df["exchange"] == "NSE") &
        (instruments_df["instrument_type"] == "EQ")
    ]

    # Combine tradingsymbol and name for matching
    symbol_name_list = nse_df["tradingsymbol"].tolist() + nse_df["name"].dropna().tolist()
    matches = get_close_matches(query.upper(), symbol_name_list, n=max_results, cutoff=0.4)

    # Filter matching results from the DataFrame
    filtered_df = nse_df[
        nse_df["tradingsymbol"].isin(matches) | nse_df["name"].isin(matches)
    ]

    return [f"{row['tradingsymbol']} - {row['name']}" for _, row in filtered_df.iterrows()]
