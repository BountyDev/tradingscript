import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime
import requests
import pytz
import json

def send_telegram_notification(message):
    url = f"https://api.telegram.org/botAAGgrLhkh2bZZEKEFgrmtG6iJxkDEsqpwSo/sendMessage"
    payload = {
        'chat_id': "7542116178",
        'text': message
    }
    try:
        requests.post(url, json=payload)
        print("Telegram notification sent.")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")


# Add this function to get CST time
def get_current_cst_time():
    cst = pytz.timezone('US/Central')
    return datetime.now(cst).strftime('%Y-%m-%d %H:%M:%S')

# Constants
API_KEY = 'mx0vglNKnod8HafqPx'
API_SECRET = '665463bee8334a1891582a42fe7d5e79'
SYMBOL = 'SOL/USDT'
LEVERAGE = 50  # Modify to 100 for 100x leverage
RISK_REWARD_RATIO = 70 / 30  # 70% gain to 30% stop-loss
TRADE_AMOUNT_USD = 10  # Fixed trade amount in USD

# Initialize exchange
exchange = ccxt.mexc({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {
        'defaultType': 'future',
    },
})

def set_leverage(symbol, leverage):
    markets = exchange.load_markets()
    market = markets[symbol]
    response = exchange.private_post_position_leverage({
        'symbol': market['id'],  # Use the internal ID for the symbol
        'leverage': leverage,    # Set the desired leverage
    })
    print(f"Leverage set to {leverage}x for {symbol}: {response}")

# Fetch historical data
def fetch_ohlcv(symbol, timeframe='1m', limit=150):
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

def check_trade_status(symbol):
    try:
        positions = exchange.fetch_positions()
        for position in positions:
            if position['symbol'] == symbol:
                if position['info']['status'] == 'closed':
                    reason = position['info'].get('reason', 'unknown')  # Check the API for the exact field
                    print(f"Trade closed for {symbol}. Reason: {reason}")
                    notify_trade_status(symbol, reason)
    except Exception as e:
        print(f"Error checking trade status: {e}")

# Fetch the current price
def get_current_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

# Calculate indicators
def calculate_indicators(data):
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['EMA20'] = df['close'].ewm(span=20).mean()
    df['EMA50'] = df['close'].ewm(span=50).mean()
    df['RSI'] = calculate_rsi(df['close'])
    return df

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Strategy
def determine_signal(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    if latest['EMA20'] > latest['EMA50'] and previous['EMA20'] <= previous['EMA50'] and latest['RSI'] < 70:
        return 'long'
    elif latest['EMA20'] < latest['EMA50'] and previous['EMA20'] >= previous['EMA50'] and latest['RSI'] > 30:
        return 'short'
    return None

# Execute order
def place_order(symbol, side, usd_amount, stop_loss_price, take_profit_price):
    # Get current price and calculate position size
    current_price = get_current_price(symbol)
    # Get the current time in UTC
    now_utc = datetime.now(pytz.utc)

    # Convert to CST
    cst_timezone = pytz.timezone('America/Chicago')
    now_cst = now_utc.astimezone(cst_timezone)

    # Format the time string
    formatted_time = now_cst.strftime('%H:%M:%S %Z')

    print(str(formatted_time) + " Price:" + str(current_price))
    amount = usd_amount / current_price  # Convert USD amount to base asset amount

    #params = {
    #    'stopPrice': stop_loss_price,  # Mandatory for stop-loss
    #    'reduceOnly': False,           # For opening a position
    #}
    #order = exchange.create_order(
    #    symbol=symbol,
    #    type='market',
    #    side=side,
    #    amount=amount,
    #    params=params,
    #)
    print(f"Time of Order: {formatted_time} Placing order: {side}, Amount: {usd_amount}, Current: {current_price}, SL: {stop_loss_price}, TP: {take_profit_price}")
    print(f"Order Time (CST): {get_current_cst_time()}")

    # Set Stop-Loss and Take-Profit
    #tp_sl_params = {
    #    'stopPrice': stop_loss_price,
    #    'price': take_profit_price,
    #}
    #exchange.create_order(symbol, type='take_profit_market', side=side, amount=amount, params=tp_sl_params)

# Main loop
def main():
    while True:
        try:
            data = fetch_ohlcv(SYMBOL)
            df = calculate_indicators(data)
            signal = determine_signal(df)

            if signal == 'long':
                print("Signal detected: LONG")
                close_price = df.iloc[-1]['close']
                stop_loss = close_price * (1 - 0.3 / LEVERAGE)
                take_profit = close_price * (1 + 0.7 / LEVERAGE)
                place_order(SYMBOL, 'buy', TRADE_AMOUNT_USD, stop_loss, take_profit)

            elif signal == 'short':
                print("Signal detected: SHORT")
                close_price = df.iloc[-1]['close']
                stop_loss = close_price * (1 + 0.3 / LEVERAGE)
                take_profit = close_price * (1 - 0.7 / LEVERAGE)
                place_order(SYMBOL, 'sell', TRADE_AMOUNT_USD, stop_loss, take_profit)
            else:
                now_utc = datetime.now(pytz.utc)

                # Convert to CST
                cst_timezone = pytz.timezone('America/Chicago')
                now_cst = now_utc.astimezone(cst_timezone)

                # Format the time string
                formatted_time = now_cst.strftime('%H:%M:%S %Z')
                print(f"{formatted_time} No signal detected")

            # Check trade status
            #check_trade_status(SYMBOL)

            time.sleep(60)  # Check signals every minute

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
