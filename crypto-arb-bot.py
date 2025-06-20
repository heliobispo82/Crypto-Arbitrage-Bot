import ccxt
import time
import logging
import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Valor que você está simulando investir
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT_USDT", "40"))

# Taxas de saque por moeda e corretora
WITHDRAW_FEES = {
    'TRX': {'binance': 1, 'kucoin': 1, 'gateio': 1, 'bitget': 1},
    'XRP': {'binance': 0.25, 'kucoin': 0.25, 'gateio': 0.25, 'bitget': 0.25},
    'DOGE': {'binance': 5, 'kucoin': 5, 'gateio': 5, 'bitget': 5},
    'ADA': {'binance': 1, 'kucoin': 1, 'gateio': 1, 'bitget': 1}
}

# Configura logger
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
    },
    "gateio": {
        "apiKey": os.environ["GATEIO_API_KEY"],
        "secret": os.environ["GATEIO_SECRET_KEY"]
    },
    "bitget": {
        "apiKey": os.environ["BITGET_API_KEY"],
        "secret": os.environ["BITGET_SECRET_KEY"],
        "password": os.environ["BITGET_PASSPHRASE"]
    }
}

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        log_error(f"Failed to send Telegram message: {e}")

# Símbolos monitorados
desired_symbols = ['TRX/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT']

# Taxa de operação
TRADING_FEES = {
    'binance': 0.1,
    'kucoin': 0.1,
    'gateio': 0.2,
    'bitget': 0.1
}

# Lucro mínimo real em dólares
profit_threshold_usdt = 0.50

# Inicializa exchanges
exchanges = {}
for name, keys in API_KEYS.items():
    exchanges[name] = getattr(ccxt, name)(keys)

# Logs
def log_info(msg):
    logging.info(msg)
    print(msg)

def log_error(msg):
    logging.error(msg)
    print(f"ERROR: {msg}")

# Consulta de preços
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

# Cálculo do lucro líquido real
def calculate_real_profit(buy_price, sell_price, symbol, buy_ex, sell_ex):
    base = symbol.split('/')[0]
    buy_fee_pct = TRADING_FEES[buy_ex] / 100
    sell_fee_pct = TRADING_FEES[sell_ex] / 100
    withdraw_fee = WITHDRAW_FEES.get(base, {}).get(buy_ex, 0)

    tokens_bought = TRADE_AMOUNT / buy_price
    tokens_after_fee = tokens_bought * (1 - buy_fee_pct)
    tokens_after_withdraw = tokens_after_fee - withdraw_fee
    usdt_received = tokens_after_withdraw * sell_price * (1 - sell_fee_pct)

    profit = usdt_received - TRADE_AMOUNT
    profit_pct = (profit / TRADE_AMOUNT) * 100

    return profit, profit_pct

# Limpa log se estiver grande
LOG_FILE = "arb_bot.log"
def check_log_size(max_size_mb=5):
    if os.path.exists(LOG_FILE):
        size_mb = os.path.getsize(LOG_FILE) / (1024 * 1024)
        if size_mb > max_size_mb:
            with open(LOG_FILE, "w") as f:
                f.write("")
            log_info("Arquivo de log estava grande e foi limpo.")

# LOOP principal
while True:
    try:
        check_log_size()
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

                    profit_usdt, profit_pct = calculate_real_profit(
                        buy_price, sell_price, symbol, buy_ex_name, sell_ex_name
                    )

                    # DEBUG extra (recomendado)
                    log_info(f"Lucro calculado: ${profit_usdt:.2f} ({profit_pct:.2f}%) | Limite: ${profit_threshold_usdt:.2f}")

                    # CONDIÇÃO FINAL correta
                    if profit_usdt >= profit_threshold_usdt:
                        message = (
                            f"💰 Arbitrage Opportunity!\n"
                            f"Buy on {buy_ex_name} at {buy_price:.4f}\n"
                            f"Sell on {sell_ex_name} at {sell_price:.4f}\n"
                            f"Real Profit: ${profit_usdt:.2f} ({profit_pct:.2f}%)\n"
                            f"Pair: {symbol}"
                        )
                        log_info(message)
                        send_telegram_message(message)

    except Exception as e:
        log_error(f"Fatal error: {e}")

    time.sleep(60)

    #  cd Crypto-Arbitrage-Bot

    # python crypto-arb-bot.py