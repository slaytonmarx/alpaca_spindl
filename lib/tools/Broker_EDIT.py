import alpaca_trade_api as alpaca
from slack_sdk import WebClient
import logging

def live_api(no_message:bool = False):
    if not no_message: print('Activating with Live')
    ALPACA_KEY_ID = 'YOUR_API_KEY'
    ALPACA_SECRET_KEY = 'YOUR_SECRET_KEY'
    BASE_URL = 'https://api.alpaca.markets'
    api = alpaca.REST(
        ALPACA_KEY_ID, ALPACA_SECRET_KEY, base_url=BASE_URL)
    return api

def paper_api(no_message:bool = False):
    if not no_message: print('Activating with Paper')
    ALPACA_KEY_ID = 'YOUR_API_KEY'
    ALPACA_SECRET_KEY = 'YOUR_SECRET_KEY'
    BASE_URL = 'https://paper-api.alpaca.markets'
    api = alpaca.REST(
        ALPACA_KEY_ID, ALPACA_SECRET_KEY, base_url=BASE_URL)
    return api

def slack_client():
    bot_oath = 'YOUR_BOT_OATH'
    client = WebClient(token=bot_oath) if bot_oath != 'YOUR_SLACK_BOT_OATH' else None
    logger = logging.getLogger(__name__) if bot_oath != 'YOUR_SLACK_BOT_OATH' else None
    return client, logger, 'YOUR_CHANNEL_ID'