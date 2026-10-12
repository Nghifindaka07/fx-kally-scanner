import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime, date

# ==========================================
# CONFIGURATION KEYS & PREFERENCES
# ==========================================
FINNHUB_API_KEY = "sandbox_c1234567890" 
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# MT5 Connection Credentials (Fill in your broker details)
MT5_LOGIN = 83098278          # Your account number
MT5_PASSWORD = "YourPassword" # Your MT5 main trading password
MT5_SERVER = "HFMarkets-Live"  # Exact server name from your broker profile

MARKETS = {
    "Gold (XAU/USD)": {"yf_symbol": "XAUUSD=X", "mt5_symbol": "XAUUSD"},
    "EUR/USD": {"yf_symbol": "EURUSD=X", "mt5_symbol": "EURUSD"},
    "GBP/USD": {"yf_symbol": "GBPUSD=X", "mt5_symbol": "GBPUSD"},
    "USD/JPY": {"yf_symbol": "JPY=X", "mt5_symbol": "USDJPY"}
}
TIMEFRAME = "15m"
LOT_SIZE = 0.01  # Fixed micro-lot for safety testing

# ==========================================
# METATRADER 5 INITIALIZATION
# ==========================================
print("Connecting to MetaTrader 5 Terminal...")
if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
    print(f"❌ MT5 Initialization failed. Error code: {mt5.last_error()}")
    mt5.shutdown()
    quit()
print("✅ Successfully logged into MT5 Trading Terminal.")

def execute_mt5_order(symbol, action_type, price, sl, tp):
    """ Builds and transmits structural market execution orders directly to your MT5 account """
    order_type = mt5.ORDER_TYPE_BUY if action_type == "BUY" else mt5.ORDER_TYPE_SELL
    filling_type = mt5.ORDER_FILLING_FOK # Fill or Kill standard
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": price,
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "deviation": 20,
        "magic": 20261012,  # Tracker ID for your AI trades
        "comment": "KALLY07 AI AUTOMATION",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Order Execution Failed for {symbol}. Code: {result.retcode}")
    else:
        print(f"🔥 LIVE ORDER PLACED SUCCESSFULLY: {action_type} {symbol} at {price}")

# ==========================================
# LIVE FUNDAMENTAL STREAMING DATA
# ==========================================
today_str = date.today().strftime('%Y-%m-%d')
url = f"https://finnhub.io{today_str}&to={today_str}&token={FINNHUB_API_KEY}"
fund_bias = "NEUTRAL"
try:
    res = requests.get(url, timeout=10).json().get('economicCalendar', [])
    df_cal = pd.DataFrame(res)
    if not df_cal.empty:
        high_impact = df_cal[df_cal['impact'].isin(['high', 'medium'])].dropna(subset=['actual', 'forecast'])
        if not high_impact.empty:
            latest_event = high_impact.iloc[-1]
            usd_is_bullish = float(latest_event['actual']) > float(latest_event['forecast'])
            fund_bias = "BULLISH_USD" if usd_is_bullish else "BEARISH_USD"
except Exception:
    pass

# ==========================================
# CORE ALGO DISPATCH LOOP
# ==========================================
for name, target in MARKETS.items():
    try:
        yf_sym = target["yf_symbol"]
        mt5_sym = target["mt5_symbol"]
        
        df = yf.download(yf_sym, period="2d", interval=TIMEFRAME, auto_adjust=False, progress=False)
        if df.empty or len(df) < 30: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Calculations
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
        tr = pd.concat([df["High"] - df["Low"], (df["High"] - df["Close"].shift(1)).abs()], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(14).mean()
        
        latest = df.iloc[-1]
        price, ema20, ema50, atr = float(latest["Close"]), float(latest["EMA20"]), float(latest["EMA50"]), float(latest["ATR"])
        
        recent = df.tail(20)
        swing_high, swing_low = float(recent["High"].iloc[:-1].max()), float(recent["Low"].iloc[:-1].min())
        
        tech_bullish = price > swing_high and price > ema20 > ema50
        tech_bearish = price < swing_low and price < ema20 < ema50
        is_usd_base = name.endswith("/USD)") or "Gold" in name
        
        # Convergence Logic Mapping
        final_signal = None
        if fund_bias == "BEARISH_USD" and is_usd_base and tech_bullish:
            final_signal = "BUY"
        elif fund_bias == "BULLISH_USD" and is_usd_base and tech_bearish:
            final_signal = "SELL"
            
        if final_signal:
            sl = price - (2.0 * atr) if final_signal == "BUY" else price + (2.0 * atr)
            tp = price + (4.0 * atr) if final_signal == "BUY" else price - (4.0 * atr)
            
            # Fetch current live tick price straight from MT5 link to avoid slippage mismatch
            info = mt5.symbol_info_tick(mt5_sym)
            if info is not None:
                execution_price = info.ask if final_signal == "BUY" else info.bid
                
                # TRIGGER LIVE MT5 MARKET EXECUTION
                execute_mt5_order(mt5_sym, final_signal, execution_price, sl, tp)
    except Exception as e:
        print(f"Error scanning {name}: {str(e)}")
        continue

# Clean shutdown loop protection
mt5.shutdown()
