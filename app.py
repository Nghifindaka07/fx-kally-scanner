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
FINNHUB_API_KEY = "sandbox_c1234567890"  # Replace with your premium token if preferred
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# MT5 Client Account Parameters
MT5_LOGIN = 83098278                 # Your active account number
MT5_PASSWORD = "YourSecurePassword"  # Your main terminal trading password
MT5_SERVER = "HFMarkets-Live"         # Exact broker server name

RISK_PERCENT = 0.01  # Dynamically calculate lot sizes based on 1% account equity risk

MARKETS = {
    "Gold (XAU/USD)": {"yf_symbol": "XAUUSD=X", "mt5_symbol": "XAUUSD"},
    "EUR/USD": {"yf_symbol": "EURUSD=X", "mt5_symbol": "EURUSD"},
    "GBP/USD": {"yf_symbol": "GBPUSD=X", "mt5_symbol": "GBPUSD"},
    "USD/JPY": {"yf_symbol": "JPY=X", "mt5_symbol": "USDJPY"}
}
PRIMARY_TIMEFRAME = "15m"

# ==========================================
# METATRADER 5 CORE RUNTIME CONNECTION
# ==========================================
print("[*] Launching MetaTrader 5 Bridge Link...")
if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
    print(f"[-] MT5 Terminal API Connection failed. Error Code: {mt5.last_error()}")
    mt5.shutdown()
    quit()
print("[+] Synchronized successfully with MetaTrader 5 active account workspace.")

# ==========================================
# AUTOMATED LOT SIZING & RISK MATRIX
# ==========================================
def calculate_dynamic_lot_size(symbol, stop_loss_distance, risk_percent=RISK_PERCENT):
    """ Dynamically calculates exact lot sizes targeting precisely 1% total balance risk """
    account_info = mt5.account_info()
    if account_info is None:
        return 0.01  # Safest minimum micro-lot fallback
        
    balance = account_info.balance
    risk_amount = balance * risk_percent
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return 0.01
        
    trade_size_value = symbol_info.trade_contract_size  # Typically 100,000 for Forex, 100 for Gold
    
    if stop_loss_distance == 0:
        return 0.01
        
    # Calculate target lot size value based on contractual pricing formulas
    raw_lot_size = risk_amount / (stop_loss_distance * trade_size_value)
    
    # Bound parameters within allowed broker specifications
    min_lot = symbol_info.volume_min
    max_lot = symbol_info.volume_max
    step_lot = symbol_info.volume_step
    
    refined_lot = round(raw_lot_size / step_lot) * step_lot
    return max(min(refined_lot, max_lot), min_lot)

# ==========================================
# BROADCAST NOTIFICATION PIPELINE
# ==========================================
def broadcast_alert_to_discord(webhook_url, market, action, price, sl, tp, logic):
    if not webhook_url:
        return
    color_map = {"STRONG BUY 🔥": 2424064, "STRONG SELL 🔥": 15671124}
    payload = {
        "username": "KALLY07 AUTOMATION BOT",
        "embeds": [{
            "title": "🚨 LIVE ALGORITHMIC TRADE EXECUTED",
            "description": f"**Asset Vector:** `{market}`\n**Action Bias:** __{action}__",
            "color": color_map.get(action, 8421504),
            "fields": [
                {"name": "📈 Entry Execution", "value": f"`{price:.5f}`", "inline": True},
                {"name": "🛡️ Risk Barrier (SL)", "value": f"`{sl:.5f}`", "inline": True},
                {"name": "🎯 Target Take Profit", "value": f"`{tp:.5f}`", "inline": True},
                {"name": "🧠 Core Convergence Rules", "value": logic, "inline": False}
            ],
            "footer": {"text": "KALLY07 FX VISIONARIES Engine Flow"}
        }]
    }
    try: requests.post(webhook_url, json=payload, timeout=10)
    except Exception: pass

def execute_mt5_market_order(symbol, action_type, price, sl, tp, computed_lots):
    """ Transmits market execution structures directly onto broker server systems """
    order_direction = mt5.ORDER_TYPE_BUY if action_type == "BUY" else mt5.ORDER_TYPE_SELL
    
    order_blueprint = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": round(computed_lots, 2),
        "type": order_direction,
        "price": price,
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "deviation": 15,
        "magic": 20261012,
        "comment": "KALLY07 CONVERGENCE LIVE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    
    order_dispatch = mt5.order_send(order_blueprint)
    if order_dispatch.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[-] Transmission Failure on {symbol}. Broker Code Feedback: {order_dispatch.retcode}")
    else:
        print(f"[+] SUCCESS: Executed {action_type} {symbol} | Vol: {computed_lots} lots | Entry: {price}")

# ==========================================
# RESILIENT TECHNICAL DATA PIPELINE
# ==========================================
def resilient_market_fetch(ticker, target_interval):
    """ Uses secondary and tertiary timeframes if standard intraday data fails """
    try:
        data = yf.download(ticker, period="4d", interval=target_interval, auto_adjust=False, progress=False)
        if data.empty or len(data) < 25:
            # Fallback 1: Hourly Candles
            data = yf.download(ticker, period="7d", interval="1h", auto_adjust=False, progress=False)
        if data.empty or len(data) < 25:
            # Fallback 2: Daily Structural Candles
            data = yf.download(ticker, period="45d", interval="1d", auto_adjust=False, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data.dropna(subset=["Open", "High", "Low", "Close"])
    except Exception:
        return pd.DataFrame()

# ==========================================
# LIVE ECONOMIC MACRO ASSESSMENT
# ==========================================
today_str = date.today().strftime('%Y-%m-%d')
macro_url = f"https://finnhub.io{today_str}&to={today_str}&token={FINNHUB_API_KEY}"
fund_bias = "NEUTRAL"

try:
    calendar_res = requests.get(macro_url, timeout=10).json().get('economicCalendar', [])
    df_cal = pd.DataFrame(calendar_res)
    if not df_cal.empty:
        active_news = df_cal[df_cal['impact'].isin(['high', 'medium'])].dropna(subset=['actual', 'forecast'])
        if not active_news.empty:
            latest_release = active_news.iloc[-1]
            usd_is_bullish = float(latest_release['actual']) > float(latest_release['forecast'])
            fund_bias = "BULLISH_USD" if usd_is_bullish else "BEARISH_USD"
except Exception:
    pass

# ==========================================
# MATRIX AUTOMATION CRON DISPATCHER LOOP
# ==========================================
print(f"[*] Processing Macro Target Matrix: Current Base Focus Is {fund_bias}...")

for friendly_name, configuration in MARKETS.items():
    yf_symbol = configuration["yf_symbol"]
    mt5_symbol = configuration["mt5_symbol"]
    
    df_candles = resilient_market_fetch(yf_symbol, PRIMARY_TIMEFRAME)
    if df_candles.empty or len(df_candles) < 25:
        print(f"[-] Data layers for asset stream {friendly_name} unavailable. Skipping asset class loop.")
        continue
        
    # Technical Indicators Calculations
    df_candles["EMA20"] = df_candles["Close"].ewm(span=20, adjust=False).mean()
    df_candles["EMA50"] = df_candles["Close"].ewm(span=50, adjust=False).mean()
    true_range = pd.concat([
        df_candles["High"] - df_candles["Low"], 
        (df_candles["High"] - df_candles["Close"].shift(1)).abs()
    ], axis=1).max(axis=1)
    df_candles["ATR"] = true_range.rolling(14).mean()
    
    last_row = df_candles.iloc[-1]
    current_close, ema20, ema50, atr = float(last_row["Close"]), float(last_row["EMA20"]), float(last_row["EMA50"]), float(last_row["ATR"])
    
    # Structure Break Calculations
    structural_subset = df_candles.tail(20)
    local_high = float(structural_subset["High"].iloc[:-1].max())
    local_low = float(structural_subset["Low"].iloc[:-1].min())
    
    trend_up = current_close > local_high and current_close > ema20 > ema50
    trend_down = current_close < local_low and current_close < ema20 < ema50
    is_usd_base = friendly_name.endswith("/USD)") or "Gold" in friendly_name
    
    # Algorithmic Convergence Matrix Evaluation
    suggested_action = None
    justification_log = ""
    
    if fund_bias == "BEARISH_USD" and is_usd_base and trend_up:
        suggested_action = "BUY"
        justification_log = "Live macroeconomic API records weakening USD bias. Smart money technical charts confirm a clean bullish breakout sequence above local swing highs."
    elif fund_bias == "BULLISH_USD" and is_usd_base and trend_down:
        suggested_action = "SELL"
        justification_log = "Live macroeconomic API records expansionary USD acceleration. Price metrics broken past major lower structure floors."
        
    if suggested_action:
        # ATR Safety Calculation Multipliers
        stop_loss_distance = 2.5 * atr
        sl_level = current_close - stop_loss_distance if suggested_action == "BUY" else current_close + stop_loss_distance
        tp_level = current_close + (5.0 * atr) if suggested_action == "BUY" else current_close - (5.0 * atr)
        
        # Pull real-time quote parameters directly from broker execution server spread logs
        mt5.symbol_select(mt5_symbol, True)
        tick_metrics = mt5.symbol_info_tick(mt5_symbol)
        
        if tick_metrics is not None:
            live_entry_price = tick_metrics.ask if suggested_action == "BUY" else tick_metrics.bid
            
            # Dynamically sizing capital distribution
            exact_lots_allowed = calculate_dynamic_lot_size(mt5_symbol, stop_loss_distance)
