import streamlit as st
import pandas as pd
import requests
import altair as alt
import datetime

st.set_page_config(page_title="NSE Stock Analysis", layout="wide")

# -------------------------
# NSE DIRECT API FUNCTIONS
# -------------------------
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}

def get_quote(symbol):
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    response = session.get(url, headers=headers)
    return response.json()

def get_history(symbol, start_date="2023-01-01"):
    url = (
        f"https://www.nseindia.com/api/historical/cm/equity?"
        f"symbol={symbol}&series=[%22EQ%22]&from={start_date}&to=2099-12-31"
    )
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    response = session.get(url, headers=headers)
    data = response.json()

    df = pd.DataFrame(data["data"])
    df["CH_TIMESTAMP"] = pd.to_datetime(df["CH_TIMESTAMP"])
    return df


# -------------------------
# STREAMLIT UI
# -------------------------
st.title("📈 NSE Stock Analysis (matplotlib-free)")

symbol = st.text_input("Enter NSE Symbol", "RELIANCE").upper()
days = st.slider("Number of Days to View", 30, 365, 180)

if st.button("Load Data"):
    try:
        # --------------------------------
        # 1. GET LIVE QUOTE
        # --------------------------------
        quote = get_quote(symbol)
        st.subheader("📌 Live Price")
        st.write(f"**Last Price:** ₹{quote['priceInfo']['lastPrice']:,}")
        st.write(f"**Open:** ₹{quote['priceInfo']['open']:,}")
        st.write(f"**High:** ₹{quote['priceInfo']['intraDayHighLow']['max']:,}")
        st.write(f"**Low:** ₹{quote['priceInfo']['intraDayHighLow']['min']:,}")

        # --------------------------------
        # 2. HISTORICAL DATA
        # --------------------------------
        df = get_history(symbol)
        df = df.rename(columns={
            "CH_TIMESTAMP": "Date",
            "CH_OPENING_PRICE": "Open",
            "CH_CLOSING_PRICE": "Close",
            "CH_TRADE_HIGH_PRICE": "High",
            "CH_TRADE_LOW_PRICE": "Low",
            "CH_TOT_TRADED_QTY": "Volume",
        })

        df = df.sort_values("Date").tail(days)

        st.subheader("📄 Historical Data")
        st.dataframe(df, use)    
