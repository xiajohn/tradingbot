import alpaca_trade_api as tradeapi
import pandas as pd
import yfinance as yf
from datetime import date, timedelta

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access API keys and base URL from environment variables
API_KEY = os.getenv('ALPACA_API_KEY')
API_SECRET = os.getenv('ALPACA_API_SECRET')
BASE_URL = os.getenv('ALPACA_BASE_URL')

# Initialize Alpaca API
import alpaca_trade_api as tradeapi
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

# Your existing code continues here...


# Unified function to fetch historical market data
def fetch_historical_data(symbol, period=None, start_date=None, end_date=None):
    """
    Fetches historical market data.
    - For momentum: Provide `period='6mo'` for the last 6 months.
    - For moving averages: Provide `start_date` and `end_date` as ISO format strings.
    """
    ticker = yf.Ticker(symbol)
    if period:
        hist = ticker.history(period=period)
    else:
        hist = ticker.history(start=start_date, end=end_date)
    return hist

# Fetch financial ratios
def fetch_pe_ratio(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info.get('forwardPE', 0)  # Return 0 if not found

def fetch_pb_ratio(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info.get('priceToBook', 0)  # Return 0 if not found

# Calculate momentum and normalize scores
def calculate_momentum_score(closing_prices):
    if closing_prices.empty:
        return 0
    return closing_prices.iloc[-1] / closing_prices.iloc[0] - 1

def normalize_scores(scores):
    min_score, max_score = min(scores), max(scores)
    return [(score - min_score) / (max_score - min_score) for score in scores]

# Composite score calculation
def calculate_composite_score(symbol):
    try:
        pe_ratio = fetch_pe_ratio(symbol)
        pb_ratio = fetch_pb_ratio(symbol)
        hist = fetch_historical_data(symbol, period='6mo')
        if hist.empty:
            return 0

        momentum = calculate_momentum_score(hist['Close'])
        pe_score = 1 / pe_ratio if pe_ratio > 0 else 0
        pb_score = 1 / pb_ratio if pb_ratio > 0 else 0
        
        scores = normalize_scores([pe_score, pb_score, momentum])
        return sum(scores) / len(scores)
    except Exception as e:
        print(f"Error with {symbol}: {e}")
        return 0

# Function to calculate moving averages
def calculate_moving_averages(symbol, start_date, end_date):
    df = fetch_historical_data(symbol, start_date=start_date, end_date=end_date)
    df['SMA'] = df['Close'].rolling(window=20).mean()
    df['LMA'] = df['Close'].rolling(window=50).mean()
    return df

# Decide action based on moving averages
def decide_action(df):
    latest, prev = df.iloc[-1], df.iloc[-2]
    if pd.isna(latest['SMA']) or pd.isna(latest['LMA']):
        return 'Hold', latest['Close']
    if latest['SMA'] > latest['LMA'] and prev['SMA'] <= prev['LMA']:
        return 'Buy', latest['Close']
    elif latest['SMA'] < latest['LMA'] and prev['SMA'] >= prev['LMA']:
        return 'Sell', latest['Close']
    else:
        return 'Hold', latest['Close']

# Check if can sell
def can_sell(symbol, qty):
    positions = api.list_positions()
    for position in positions:
        if position.symbol == symbol and int(position.qty) >= qty:
            return True
    return False

# Place order with selling check
def place_order(symbol, qty, action):
    if action == 'Sell' and not can_sell(symbol, qty):
        print(f"Cannot sell {qty} shares of {symbol}. Insufficient shares.")
        return
    print(f"Placing {action} order for {qty} shares of {symbol}.")
    api.submit_order(symbol=symbol, qty=qty, side=action.lower(), type='market', time_in_force='gtc')

# Main trading logic
symbols = [
    'TSLA', 'NVDA', 'AMZN', 'AAPL', 'MSFT',
    'GOOGL', 'META', 'BABA', 'NFLX', 'ADBE',
    'JNJ', 'V', 'PG', 'UNH', 'DIS',
    'MA', 'HD', 'VZ', 'INTC', 'CSCO',
    'PFE', 'MRK', 'WMT', 'BA', 'KO',
    'XOM', 'CVX', 'ABBV', 'MCD', 'TMO',
    'NKE', 'DHR', 'ACN', 'ABT', 'CRM',
    'LLY', 'ORCL', 'COST', 'QCOM', 'UPS'
]
today = date.today()
start_date = today - timedelta(days=365)
end_date = today

scores = {symbol: calculate_composite_score(symbol) for symbol in symbols}
sorted_symbols = sorted(scores, key=scores.get, reverse=True)
to_buy = sorted_symbols[:len(sorted_symbols) // 5]
to_sell = sorted_symbols[-len(sorted_symbols) // 5:]

print(f"To Buy: {to_buy}\nTo Sell: {to_sell}")

for symbol in symbols:
    df = calculate_moving_averages(symbol, start_date.isoformat(), end_date.isoformat())
    action, price = decide_action(df)
    print(f"{symbol}: Moving average - Action: {action} at price {price}")
    if action in ['Buy', 'Sell']:
        place_order(symbol, 8, action)

for symbol in to_buy:  
    print(f"{symbol}: Composite - Action: buy")
    place_order(symbol, 8, 'Buy')
        
for symbol in to_sell:  
    print(f"{symbol}: Composite - Action: buy")
    place_order(symbol, 8, 'Sell')
