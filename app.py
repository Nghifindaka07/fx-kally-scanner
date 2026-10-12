import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, date

# ==========================================
# CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="KALLY07 FX VISIONARIES AI",
    page_icon="👑",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #080b12; color: #f5f5f5; }
    h1, h2, h3, h4 { color: #d4af37 !important; }
    [data-testid="stMetric"] {
        background-color: #141a26;
        border: 1px solid #d4af37;
        padding: 12px;
        border-radius: 10px;
    }
    .stButton > button {
        background-color: #d4af37;
        color: #080b12;
        font-weight: bold;
        border-radius: 8px;
    }
    .news-box {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("👑 KALLY07 FX VISIONARIES AI v4.0")
st.caption("HYBRID MACRO ENGINE WITH WEBHOOK BROADCAST CAPABILITIES")

# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.title("⚙️ Control & Webhooks")
market = st.sidebar.selectbox(
    "Select Asset Pair",
    ["Gold (XAU/USD)", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]
)
timeframe = st.sidebar.selectbox(
    "Technical Chart Interval", ["5 minutes (M5)", "15 minutes (M15)", "1 hour (H1)"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 API Integrations")
FINNHUB_API_KEY = st.sidebar.text_input("Finnhub API Key", value="sandbox_c1234567890", type="password")
DISCORD_WEBHOOK_URL = st.sidebar.text_input("Discord Webhook URL", value="", type="password")

symbol_map = {
    "Gold (XAU/USD)": "XAUUSD=X", "EUR/USD": "EURUSD=X", 
    "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X", 
    "AUD/USD": "AUDUSD=X", "USD/CAD": "CAD=X"
}
symbol = symbol_map[market]
interval = "5m" if "M5" in timeframe else "15m" if "M15" in timeframe else "1h"

# ==========================================
# DISCORD BROADCAST MODULE
# ==========================================
def broadcast_signal_to_discord(webhook_url, market_name, timeframe_val, action, price_val, sl_val, tp_val, logic_desc):
    if not webhook_url or webhook_url.strip() == "":
        return False
        
    color_map = {
        "STRONG BUY 🔥": 2424064,  
        "STRONG SELL 🔥": 15671124, 
        "TECHNICAL BUY": 3447003,   
        "TECHNICAL SELL": 10040012  
    }
    
    embed_color = color_map.get(action, 8421504)
    
    payload = {
        "username": "KALLY07 AI VISIONARY ALERTS",
        "embeds": [
            {
                "title": f"🚨 NEW MARKET CONVERGENCE IDENTIFIED",
                "description": f"**Asset:** `{market_name}`\n**Timeframe:** `{timeframe_val}`\n**Action Bias:** __{action}__",
                "color": embed_color,
                "fields": [
                    {"name": "📈 Suggested Entry", "value": f"`{price_val:.5f}`", "inline": True},
                    {"name": "🛡️ Safety Stop Loss", "value": f"`{sl_val:.5f}`", "inline": True},
                    {"name": "🎯 Take Profit target", "value": f"`{tp_val:.5f}`", "inline": True},
                    {"name": "🧠 Algorithmic Justification", "value": logic_desc, "inline": False}
                ],
                "footer": {
                    "text": f"KALLY07 AI Engine | Execution Verified: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        ]
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 204
    except Exception:
        return False

# ==========================================
# ECONOMIC CALENDAR PIPELINE
# ==========================================
@st.cache_data(ttl=30)
def load_market_data(ticker, interval_val):
    """ Loads data with a reliable daily fallback if intraday streams fail """
    try:
        # Attempt primary data grab (e.g., 5m, 15m)
        data = yf.download(ticker, period="5d", interval=interval_val, auto_adjust=False, progress=False)
        
        # Fallback 1: If intraday fails, try 1-hour intervals
        if data.empty or len(data) < 30:
            data = yf.download(ticker, period="7d", interval="1h", auto_adjust=False, progress=False)
            
        # Fallback 2: If hourly fails, try standard 1-day intervals
        if data.empty or len(data) < 30:
            data = yf.download(ticker, period="60d", interval="1d", auto_adjust=False, progress=False)
            
        if data.empty: 
            return pd.DataFrame()
            
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        return data.dropna(subset=["Open", "High", "Low", "Close"])
        
    except Exception:
        return pd.DataFrame()

# ==========================================
# AUTOMATED FUNDAMENTAL PROCESSING
# ==========================================
def auto_parse_fundamentals(df_cal, target_pair):
    if df_cal.empty:
        return "NEUTRAL", "No live data streaming from macro calendar API. Operating on pure structural technicals.", "#1f2937"
    
    high_impact_events = df_cal[df_cal['impact'].isin(['high', 'medium'])]
    if high_impact_events.empty:
        return "NEUTRAL", "Economic calendar events today are Low Impact. Market driven by pure orderflow.", "#1f2937"
    
    released = high_impact_events.dropna(subset=['actual', 'forecast'])
    if released.empty:
        incoming = high_impact_events.iloc[-1]
        return "WAIT / CAUTION", f"Upcoming High-Impact Release: **{incoming['event']}** ({incoming['country']}). Stand aside during news injections.", "#cb9300"
    
    latest_event = released.iloc[-1]
    event_name = latest_event['event']
    country = latest_event['country']
    
    try:
        actual = float(latest_event['actual'])
        forecast = float(latest_event['forecast'])
    except ValueError:
        return "NEUTRAL", "Live macro metrics processing. No definitive numeric deviation recorded.", "#1f2937"

    usd_is_bullish = False
    if actual > forecast:
        if any(keyword in event_name.lower() for keyword in ["cpi", "inflation", "ppi"]):
            usd_is_bullish = True if country == "US" else False
        else:
            usd_is_bullish = True if country == "US" else False
    else:
        usd_is_bullish = False if country == "US" else True

    is_usd_base = target_pair.endswith("/USD)") or "Gold" in target_pair

    if usd_is_bullish:
        if is_usd_base:
            return "SELL (Macro Pressure)", f"Automated Alert: **{event_name}** exceeded expectations. Strong USD exerts immediate downward pressure.", "#ef4444"
        else:
            return "BUY (Macro Tailwind)", f"Automated Alert: **{event_name}** dropped positive for USD asset quote matrix variables.", "#22c55e"
    else:
        if is_usd_base:
            return "BUY (Macro Tailwind)", f"Automated Alert: **{event_name}** missed consensus targets. Capital rotating toward commodities.", "#22c55e"
        else:
            return "SELL (Macro Pressure)", f"Automated Alert: **{event_name}** dropped negative for general dollar currency support lines.", "#ef4444"

# ==========================================
# TECHNICAL CONFIGURATIONS
# ==========================================
@st.cache_data(ttl=30)
def load_market_data(ticker, interval_val):
    data = yf.download(ticker, period="5d", interval=interval_val, auto_adjust=False, progress=False)
    if data.empty: return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna(subset=["Open", "High", "Low", "Close"])

df = load_market_data(symbol, interval)
if df.empty or len(df) < 30:
    st.error("Market asset stream unavailable.")
    st.stop()

df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
prev_close = df["Close"].shift(1)
tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev_close).abs(), (df["Low"] - prev_close).abs()], axis=1).max(axis=1)
df["ATR"] = tr.rolling(14).mean()

latest = df.iloc[-1]
price, ema20, ema50, atr = float(latest["Close"]), float(latest["EMA20"]), float(latest["EMA50"]), float(latest["ATR"])
if not np.isfinite(atr) or atr <= 0: 
    atr = float((df["High"] - df["Low"]).tail(14).mean())

recent_window = df.tail(20)
swing_high = float(recent_window["High"].iloc[:-1].max())
swing_low = float(recent_window["Low"].iloc[:-1].min())
tech_bullish = price > swing_high and price > ema20 > ema50
tech_bearish = price < swing_low and price < ema20 < ema50

# ==========================================
# AI CORE MATRIX CONVERGENCE
# ==========================================
final_signal = "HOLD / CONFLICT"
signal_color = "info"
signal_explanation = "The AI execution framework detects conflicting parameters across technical charts and live macro calculations."

if "BUY" in fund_bias and tech_bullish:
    final_signal = "STRONG BUY 🔥"
    signal_color = "success"
    signal_explanation = "CONVERGENCE VERIFIED: Smart Money market structures broke above key resistance points while live API data supports macroeconomic expansion cycles."
elif "SELL" in fund_bias and tech_bearish:
    final_signal = "STRONG SELL 🔥"
    signal_color = "error"
    signal_explanation = "CONVERGENCE VERIFIED: Market structural lows validated a complete breakdown while automated macro data highlights systematic downside pressure profiles."
elif "NEUTRAL" in fund_bias:
    if tech_bullish:
        final_signal = "TECHNICAL BUY"
        signal_color = "success"
        signal_explanation = "Bullish swing high breach confirmed. No active or conflicting macro data feeds are overriding local price structures."
    elif tech_bearish:
        final_signal = "TECHNICAL SELL"
        signal_color = "error"
        signal_explanation = "Bearish swing low breakdown confirmed."

entry = price
if "BUY" in final_signal:
    sl, tp = entry - (2.0 * atr), entry + (4.0 * atr)
elif "SELL" in final_signal:
    sl, tp = entry + (2.0 * atr), entry - (4.0 * atr)
else:
    sl, tp = None, None

# ==========================================
# USER WEBHOOK BROADCAST INTERFACE BUTTON
