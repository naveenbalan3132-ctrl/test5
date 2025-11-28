import streamlit as st
import pandas as pd
from nseindia import NseIndia
import altair as alt
import ta

st.set_page_config(page_title="NSE Stock Analysis", layout="wide")

nse = NseIndia()

st.title("📈 NSE Stock Analysis (Matplotlib-Free)")

symbol = st.text_input("Enter NSE Stock Symbol (e.g., RELIANCE)", "RELIANCE")
days = st.slider("Number of Days", 30, 365, 180)

if st.button("Load Data"):
    try:
        st.subheader(f"Fetching data for: {symbol}")

        # ------------------ LIVE QUOTE ------------------
        quote = nse.stock_quote(symbol)

        if not quote:
            st.error("Invalid symbol or NSE blocked request.")
            st.stop()

        # ------------------ HISTORICAL DATA ------------------
        hist = nse.equity_history(
            symbol=symbol,
            from_date="2023-01-01",
            to_date="2035-12-31"
        )

        if hist.empty:
            st.error("No historical data available.")
            st.stop()

        df = hist.rename(columns={
            "CH_TIMESTAMP": "Date",
            "CH_OPENING_PRICE": "Open",
            "CH_CLOSING_PRICE": "Close",
            "CH_TRADE_HIGH_PRICE": "High",
            "CH_TRADE_LOW_PRICE": "Low",
            "CH_TOT_TRADED_QTY": "Volume"
        })

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").tail(days)

        # ------------------ Indicators ------------------
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

        st.success("Data loaded successfully!")
        st.dataframe(df, use_container_width=True)

        # ------------------ Price Chart ------------------
        st.subheader("📉 Price Chart")

        base = alt.Chart(df).encode(x="Date:T")

        price_line = base.mark_line(color="#1f77b4").encode(y="Close:Q")
        sma20_line = base.mark_line(color="orange").encode(y="SMA20:Q")
        sma50_line = base.mark_line(color="green").encode(y="SMA50:Q")

        st.altair_chart(price_line + sma20_line + sma50_line, use_container_width=True)

        # ------------------ RSI Chart ------------------
        st.subheader("📈 RSI Indicator")

        rsi_chart = alt.Chart(df).mark_line().encode(
            x="Date:T",
            y="RSI:Q"
        )

        st.altair_chart(rsi_chart, use_container_width=True)

        # ------------------ Summary ------------------
        st.subheader("📊 Summary")
        st.write(f"**Latest Close Price:** ₹{df['Close'].iloc[-1]:,.2f}")
        st.write(f"**20-Day SMA:** ₹{df['SMA20'].iloc[-1]:,.2f}")
        st.write(f"**50-Day SMA:** ₹{df['SMA50'].iloc[-1]:,.2f}")
        st.write(f"**RSI:** {df['RSI'].iloc[-1]:.2f}")

    except Exception as e:
        st.error(f"Error: {e}")
