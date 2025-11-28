import streamlit as st
import pandas as pd
from nsepython import *
import ta
import altair as alt

st.set_page_config(page_title="NSE Stock Analysis", layout="wide")

st.title("📈 NSE Stock Analysis (Matplotlib-Free)")

# --------------------------- USER INPUT ---------------------------
symbol = st.text_input("Enter NSE Stock Symbol (e.g., RELIANCE)", "RELIANCE")
days = st.slider("Number of days", 30, 365, 180)

if st.button("Load Data"):
    try:
        # ---------------------- FETCH DATA ----------------------
        st.subheader(f"📥 Fetching data for: {symbol}")

        df = nse_stock_quote_fno(symbol)

        if df is None:
            st.error("Failed to fetch data. Check the symbol.")
            st.stop()

        # Fetch historical data using NSEPython
        hist = nsefetch(f"https://www.nseindia.com/api/historical/cm/equity?symbol={symbol}&series=[%22EQ%22]&from=2023-01-01&to=2030-12-31")

        if 'data' not in hist or len(hist['data']) == 0:
            st.error("Historical data unavailable for this symbol.")
            st.stop()

        df = pd.DataFrame(hist['data'])
        df['CH_TIMESTAMP'] = pd.to_datetime(df['CH_TIMESTAMP'])
        df = df.sort_values("CH_TIMESTAMP").tail(days)

        df.rename(columns={
            "CH_TIMESTAMP": "Date",
            "CH_OPENING_PRICE": "Open",
            "CH_CLOSING_PRICE": "Close",
            "CH_TRADE_HIGH_PRICE": "High",
            "CH_TRADE_LOW_PRICE": "Low",
            "CH_TOT_TRADED_QTY": "Volume",
        }, inplace=True)

        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]

        # ---------------------- INDICATORS ----------------------
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

        st.success("Data loaded successfully!")
        st.dataframe(df, use_container_width=True)

        # ---------------------- PRICE CHART ----------------------
        st.subheader("📉 Price Chart")

        chart_df = df.copy()

        price_chart = alt.Chart(chart_df).mark_line().encode(
            x="Date:T",
            y="Close:Q",
            color=alt.value("#1f77b4")
        )

        sma20_chart = alt.Chart(chart_df).mark_line().encode(
            x="Date:T",
            y="SMA20:Q",
            color=alt.value("orange")
        )

        sma50_chart = alt.Chart(chart_df).mark_line().encode(
            x="Date:T",
            y="SMA50:Q",
            color=alt.value("green")
        )

        st.altair_chart(price_chart + sma20_chart + sma50_chart, use_container_width=True)

        # ---------------------- RSI CHART ----------------------
        st.subheader("📈 RSI Indicator")

        rsi_chart = alt.Chart(chart_df).mark_line().encode(
            x="Date:T",
            y="RSI:Q",
        )

        st.altair_chart(rsi_chart, use_container_width=True)

        # ---------------------- FINAL SECTION ----------------------
        st.subheader("📊 Summary")

        st.write(f"**Latest Close Price:** {df['Close'].iloc[-1]:,.2f}")
        st.write(f"**20-Day SMA:** {df['SMA20'].iloc[-1]:,.2f}")
        st.write(f"**50-Day SMA:** {df['SMA50'].iloc[-1]:,.2f}")
        st.write(f"**Latest RSI:** {df['RSI'].iloc[-1]:.2f}")

    except Exception as e:
        st.error(f"Error: {e}")
