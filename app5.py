# app.py
import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

# Try importing NSE live libraries (optional)
try:
    from nsetools import Nse
    nse = Nse()
except Exception:
    nse = None

# Optional: nsepython / nsepy placeholders (if you prefer those libraries you'll need to install them)
# from nsepython import *   # if installed and you want to use its functions

st.set_page_config(page_title="NSE Stock Scout", layout="wide")

st.title("NSE Stock Scout — Entry / Targets / Live & Historical")

st.sidebar.header("Configuration")
index_choice = st.sidebar.selectbox("Start from:", ["Single ticker", "NIFTY 50 list"])
ticker_input = st.sidebar.text_input("Ticker (e.g. RELIANCE or TCS). For Yahoo use .NS suffix auto-added", "RELIANCE")
start_date = st.sidebar.date_input("Start date", dt.date.today() - dt.timedelta(days=365))
end_date = st.sidebar.date_input("End date", dt.date.today())
interval = st.sidebar.selectbox("Historical interval", ["1d", "1wk", "1mo"])
fetch_button = st.sidebar.button("Fetch & Analyze")

st.markdown("""
**How it works**
- Historical data fetched from Yahoo Finance (`yfinance`) using symbol `TICKER.NS`.
- Live quote attempted from `nsetools` (direct from NSE) if available; falls back to latest yfinance quote.
- Indicators: SMA20, SMA50, RSI(14), ATR(14).
- Rule-based entry/targets:
  - **Aggressive**: buy on breakout above recent high.
  - **Conservative**: buy on pullback to SMA50 (if trend up).
  - **Stop-loss**: ATR-based or support (whichever is wider).
  - **Targets**: 1× ATR distance and 2× ATR for tiered targets + measured-move from swing high.
""")

# Utility technical functions
def sma(series, window):
    return series.rolling(window=window).mean()

def rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_prev_close = (df['High'] - df['Close'].shift()).abs()
    low_prev_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/window, adjust=False).mean()
    return atr

def fetch_historical(ticker, start, end, interval="1d"):
    # Add .NS suffix if not present (for yfinance)
    yf_ticker = ticker.upper()
    if not yf_ticker.endswith(".NS"):
        yf_ticker = yf_ticker + ".NS"
    df = yf.download(yf_ticker, start=start, end=end + dt.timedelta(days=1), interval=interval, progress=False)
    if df.empty:
        st.error(f"No historical data found for {yf_ticker}.")
    else:
        df.index = pd.to_datetime(df.index)
    return df

def fetch_live_quote(ticker):
    # Try nsetools first for direct NSE quote
    symbol = ticker.upper()
    if symbol.endswith(".NS"):
        symbol = symbol[:-3]
    if nse:
        try:
            q = nse.get_quote(symbol)
            # Extract last traded price
            ltp = None
            if isinstance(q, dict):
                # nsetools returns nested structure; try common fields
                ltp = q.get('lastPrice') or q.get('lastTradedPrice') or q.get('price')
            if ltp is None:
                ltp = float(q.get('lastPrice', 0))
            return {"symbol": symbol, "ltp": float(ltp), "raw": q}
        except Exception:
            pass

    # Fallback: use yfinance fast info
    try:
        yf_ticker = ticker.upper()
        if not yf_ticker.endswith(".NS"):
            yf_ticker = yf_ticker + ".NS"
        tk = yf.Ticker(yf_ticker)
        info = tk.history(period="1d")
        if not info.empty:
            ltp = info['Close'].iloc[-1]
            return {"symbol": yf_ticker, "ltp": float(ltp), "raw": info.iloc[-1].to_dict()}
    except Exception:
        pass
    return {"symbol": ticker, "ltp": None, "raw": None}

def analyze(df):
    df = df.copy()
    df['SMA20'] = sma(df['Close'], 20)
    df['SMA50'] = sma(df['Close'], 50)
    df['RSI14'] = rsi(df['Close'], 14)
    df['ATR14'] = atr(df, 14)
    return df

def suggest_trades(df):
    last = df.iloc[-1]
    close = last['Close']
    sma20 = last['SMA20']
    sma50 = last['SMA50']
    rsi14 = last['RSI14']
    atr14 = last['ATR14']

    suggestions = {}
    trend_up = (sma20 > sma50) if (not pd.isna(sma20) and not pd.isna(sma50)) else False

    # Aggressive: breakout above recent 20-day high
    recent_high = df['High'].rolling(window=20).max().iloc[-1]
    if close > recent_high:
        suggestions['Aggressive'] = {
            "action": "Consider BUY (breakout)",
            "entry": close,
            "stop_loss": max(close - 2 * atr14, df['Low'].rolling(20).min().iloc[-1]),
            "targets": [close + 1 * atr14, close + 2 * atr14]
        }
    else:
        suggestions['Aggressive'] = {
            "action": "No breakout",
            "entry": None
        }

    # Conservative: pullback to SMA50 if trend up
    if trend_up and close < sma50:
        suggestions['Conservative'] = {
            "action": "Consider BUY (pullback to trend)",
            "entry": round(sma50, 2),
            "stop_loss": round(sma50 - 2 * atr14, 2),
            "targets": [round(sma50 + 1 * atr14, 2), round(sma50 + 2 * atr14, 2)]
        }
    elif trend_up and close >= sma50:
        suggestions['Conservative'] = {
            "action": "Trend up and above SMA50 — wait for a pullback or buy small",
            "entry": None
        }
    else:
        suggestions['Conservative'] = {"action": "No conservative setup", "entry": None}

    # Momentum/overbought check
    suggestions['Momentum'] = {
        "RSI14": round(rsi14, 2),
        "note": "Overbought (RSI>70) or Oversold (RSI<30) checks"
    }

    return suggestions

# UI: If user selects NIFTY 50 list, we can load a small bundled list (NIFTY50 tickers)
NIFTY50_SAMPLE = ["RELIANCE","TCS","HDFCBANK","INFY","HINDUNILVR","ICICIBANK","KOTAKBANK","LT","SBIN","AXISBANK"]

if index_choice == "NIFTY 50 list":
    tickers = st.text_area("Tickers (one per line) — or leave default", "\n".join(NIFTY50_SAMPLE)).splitlines()
else:
    tickers = [ticker_input.strip()]

if fetch_button:
    for t in tickers:
        st.header(f"Analysis for {t.upper()}")
        with st.spinner(f"Fetching historical data for {t}..."):
            df = fetch_historical(t, pd.to_datetime(start_date), pd.to_datetime(end_date), interval)
            if df is None or df.empty:
                st.warning("No data — skipping.")
                continue

        df = analyze(df)
        st.subheader("Latest indicators")
        latest = df.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Last Close", f"{latest['Close']:.2f}")
        col2.metric("SMA20", f"{latest['SMA20']:.2f}" if not pd.isna(latest['SMA20']) else "n/a")
        col3.metric("SMA50", f"{latest['SMA50']:.2f}" if not pd.isna(latest['SMA50']) else "n/a")
        col4.metric("RSI14", f"{latest['RSI14']:.2f}")

        # Live quote
        live = fetch_live_quote(t)
        if live.get("ltp") is not None:
            st.write(f"**Live quote (best available source):** {live['symbol']} — LTP = {live['ltp']:.2f}")
        else:
            st.write("Live quote not available via free API; using latest historical close.")

        # Chart
        st.subheader("Price chart (Close, SMA20, SMA50)")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df.index, df['Close'], label='Close')
        if not df['SMA20'].isna().all(): ax.plot(df.index, df['SMA20'], label='SMA20')
        if not df['SMA50'].isna().all(): ax.plot(df.index, df['SMA50'], label='SMA50')
        ax.set_ylabel("Price (INR)")
        ax.legend()
        ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=25)
        st.pyplot(fig)

        # Suggestions
        suggestions = suggest_trades(df)
        st.subheader("Rule-based suggestions (NOT financial advice)")
        st.json(suggestions)

        # Dataframe preview with indicators
        st.subheader("Recent data sample")
        st.dataframe(df[['Close','SMA20','SMA50','RSI14','ATR14']].tail(50))

st.markdown("---")
st.info("This app uses public/free data sources (yfinance / NSE wrappers). For production / live trading use providers with guarantees and/or broker APIs.")
