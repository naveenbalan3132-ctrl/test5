import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

# NSE Libraries
from nsetools import Nse
from nsepython import nsefetch, index_df

nse = Nse()

st.set_page_config(page_title="Pure NSE Stock Analyzer", layout="wide")
st.title("📈 NSE Stock Analyzer — Only NSE Data (No YFinance)")

# Sidebar
ticker = st.sidebar.text_input("Enter NSE Symbol (e.g. RELIANCE, TCS, SBIN)", "RELIANCE")
start_date = st.sidebar.date_input("Start Date", dt.date.today() - dt.timedelta(days=365))
end_date = st.sidebar.date_input("End Date", dt.date.today())
fetch_btn = st.sidebar.button("Fetch & Analyze")

# ---------------------------------------------
# HISTORICAL DATA FROM NSEPYTHON
# ---------------------------------------------
def get_nse_history(symbol):
    try:
        url = f"https://www.nseindia.com/api/chart-databyindex?index={symbol}EQN"
        data = nsefetch(url)

        candles = data["grapthData"]
        df = pd.DataFrame(candles, columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
        df.rename(columns={"timestamp": "Date", "close": "Close"}, inplace=True)
        df.set_index("Date", inplace=True)

        # fake OHLC since NSE API returns only close data
        df["Open"] = df["Close"]
        df["High"] = df["Close"]
        df["Low"] = df["Close"]

        return df

    except Exception as e:
        st.error(f"Error fetching NSE data: {e}")
        return None


# ---------------------------------------------
# LIVE QUOTE FROM NSETTOOLS
# ---------------------------------------------
def get_live_price(symbol):
    try:
        q = nse.get_quote(symbol)
        return float(q["lastPrice"])
    except:
        return None


# ---------------------------------------------
# Technical Indicators
# ---------------------------------------------
def sma(series, window):
    return series.rolling(window).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period).mean()
    avg_loss = loss.ewm(alpha=1/period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ---------------------------------------------
# Trade Logic
# ---------------------------------------------
def trade_signals(df):
    last = df.iloc[-1]

    close = last["Close"]
    sma20 = last["SMA20"]
    sma50 = last["SMA50"]
    atr14 = last["ATR14"]

    signals = {}

    # Trend check
    trend_up = sma20 > sma50

    # Breakout Logic
    recent_high = df["High"].tail(20).max()
    if close > recent_high:
        signals["Breakout Buy"] = {
            "Entry": close,
            "Stoploss": close - 2 * atr14,
            "Target 1": close + atr14,
            "Target 2": close + 2 * atr14
        }
    else:
        signals["Breakout Buy"] = "No breakout"

    # Pullback Buy
    if trend_up and close < sma50:
        signals["Pullback Buy"] = {
            "Entry": sma50,
            "Stoploss": sma50 - 2 * atr14,
            "Target 1": sma50 + atr14,
            "Target 2": sma50 + 2 * atr14
        }
    else:
        signals["Pullback Buy"] = "No pullback trade"

    return signals


# ---------------------------------------------
# MAIN PROCESS
# ---------------------------------------------
if fetch_btn:

    st.subheader(f"🔍 Fetching NSE data for: **{ticker}**")

    df = get_nse_history(ticker)

    if df is None or df.empty:
        st.error("Failed to load NSE Data.")
        st.stop()

    # Filter date range
    df = df.loc[start_date:end_date]

    # Indicators
    df["SMA20"] = sma(df["Close"], 20)
    df["SMA50"] = sma(df["Close"], 50)
    df["RSI14"] = rsi(df["Close"], 14)
    df["ATR14"] = atr(df, 14)

    # Live Price
    live = get_live_price(ticker)
    if live:
        st.metric("Live Price", f"₹ {live}")
    else:
        st.write("Live price unavailable")

    # Chart
    st.subheader("📉 Price Chart")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df.index, df["Close"], label="Close")
    ax.plot(df.index, df["SMA20"], label="SMA20")
    ax.plot(df.index, df["SMA50"], label="SMA50")
    plt.xticks(rotation=30)
    plt.legend()
    st.pyplot(fig)

    # Signals
    st.subheader("📌 Trade Suggestions (NSE-only Data)")
    signals = trade_signals(df)
    st.json(signals)

    st.subheader("📄 Recent Data")
    st.dataframe(df.tail(30))
