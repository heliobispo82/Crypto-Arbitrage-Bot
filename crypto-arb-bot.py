import ccxt
import time
import logging
import os
from dotenv import load_dotenv
load_dotenv()

# Initialize the logging system
logging.basicConfig(filename='arb_bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# API Keys
API_KEYS = {
    "binance": {
        "apiKey": os.environ["BINANCE_API_KEY"],
        "secret": os.environ["BINANCE_API_SECRET"]
    },
    "kucoin": {
        "apiKey": os.environ["KUCOIN_API_KEY"],
        "secret": os.environ["KUCOIN_SECRET_KEY"],
        "password": os.environ["KUCOIN_PASSPHRASE"]
    }
}

import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        log_error(f"Failed to send Telegram message: {e}")

# Initialize exchanges
desired_symbols = ['TRX/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT']
TRADING_FEES = {'binance': 0.1, 'kucoin': 0.1}  # in percent
profit_threshold = 0.5
exchanges = {}

for name, keys in API_KEYS.items():
    exchanges[name] = getattr(ccxt, name)(keys)

# Logging utils
def log_info(msg):
    logging.info(msg)
    print(msg)

def log_error(msg):
    logging.error(msg)
    print(f"ERROR: {msg}")

# Fetch prices
def get_prices():
    prices = {}
    for name, ex in exchanges.items():
        for symbol in desired_symbols:
            try:
                ticker = ex.fetch_ticker(symbol)
                prices[f"{name} - {symbol}"] = ticker['last']
            except Exception as e:
                log_error(f"Error fetching from {name}: {e}")
    return prices

# Profit calc
def calculate_profit(buy_price, sell_price, buy_ex, sell_ex):
    buy_fee = TRADING_FEES[buy_ex] / 100
    sell_fee = TRADING_FEES[sell_ex] / 100
    effective_buy = buy_price * (1 + buy_fee)
    effective_sell = sell_price * (1 - sell_fee)
    return ((effective_sell - effective_buy) / effective_buy) * 100

# Main loop
while True:
    try:
        prices = get_prices()
        log_info(prices)

        for symbol in desired_symbols:
            for sell_ex_name, sell_ex in exchanges.items():
                sell_price = prices.get(f"{sell_ex_name} - {symbol}")
                if not sell_price:
                    continue

                for buy_ex_name, buy_ex in exchanges.items():
                    if buy_ex_name == sell_ex_name:
                        continue

                    buy_price = prices.get(f"{buy_ex_name} - {symbol}")
                    if not buy_price:
                        continue

                    profit = calculate_profit(buy_price, sell_price, buy_ex_name, sell_ex_name)
                    print(f"{symbol}: {buy_ex_name} → {buy_price}, {sell_ex_name} → {sell_price}, profit: {profit:.2f}%")
                    if profit >= profit_threshold:
                        message = (f"💰 Arbitrage Opportunity!\n"
                                   f"Buy on {buy_ex_name} at {buy_price:.4f}\n"
                                   f"Sell on {sell_ex_name} at {sell_price:.4f}\n"
                                   f"Profit: {profit:.2f}%\n"
                                   f"Pair: {symbol}")
                        log_info(message)
                        send_telegram_message(message)

    except Exception as e:
        log_error(f"Fatal error: {e}")

    time.sleep(5)

    #  cd Crypto-Arbitrage-Bot

    # python crypto-arb-bot.py