import sys; sys.path.append('../lib/*/*'); sys.path.append('..')
from lib.tools.Gambit import Gambit
from lib.RoboTrader import RoboTrader
from lib.Portfolio import Portfolio
import metadata.trade_configs.Globals as gb
import lib.tools.Broker as br
import matplotlib.pyplot as plt
import pandas as pd
import lib.tools.Toolbox as tb
import lib.tools.TimeKeeper as tk
import alpaca_trade_api as alp
import sys

args = sys.argv
if '-p' in args: api = br.paper_api()
elif '-l' in args: api = br.live_api()
else: api = br.live_api() if input('Watch paper or live? (p/l) ').upper() == 'L' else br.paper_api()
if len(args) > 1: symbol = args[1]
else: symbol = input('What symbol?: ').upper()
portfolio = Portfolio(api)
qty = 300

def get_alp_price(api, symbol):
    df = api.get_trades(symbol, start=tk.dto_time(tk.now()-pd.DateOffset(seconds=2)), end=tk.dto_time(tk.now())).df
    if len(df) == 0: df = api.get_trades(symbol, start=tk.dto_time(tk.now()-pd.DateOffset(seconds=5)), end=tk.dto_time(tk.now())).df
    if len(df) == 0: return None
    return df.price.mean()

def whole_trader(symbol, qty, portfolio):
    while True:
        print("NEW TRADE")
        if not portfolio.has_stock(symbol):
            print("\tNO STOCK FOUND: Buy or Shortsell (b/s)")
            buy_or_sell = input('\tBuy or Sell (b/s): ')
            price = get_alp_price(portfolio.api, symbol)
            if buy_or_sell.upper() == 'B' or buy_or_sell.upper() == 'BUY':
                print('\tATTEMPTIMG BUY for',round(price,2))
                g = Gambit(portfolio, symbol, price, qty, 'buy')
            elif buy_or_sell.upper() == 'S' or buy_or_sell.upper() == 'SELL':
                print('\tATTEMPTIMG SHORTSELL for',round(price,2))
                g = Gambit(portfolio, symbol, price, qty, 'shortsell')
        else:
            print("\tSTOCK FOUND, Clear? (c)")
            clear = input('\tClear??? (c): ')
            price = get_alp_price(portfolio.api, symbol)
            print(clear)
            if clear.upper() == 'C' or clear.upper() == 'CLEAR':
                print('\tATTEMPTIMG TO CLEAR for',round(price,2))
                if portfolio.get_stock_sign(symbol): g = Gambit(portfolio, symbol, price, portfolio.get_qty(symbol), 'sell')
                else: g = Gambit(portfolio, symbol, price, portfolio.get_qty(symbol), 'shortbuy')

def enter_long_commands(command, portfolio, symbol, qty, price):
    match command:
        case 'b':
            print('\tATTEMPTIMG little BUY for',round(price,2))
            g = Gambit(portfolio, symbol, price, qty, 'buy', buffer=gb.S_LIVE_BUFFER)
        case 'B':
            print('\tATTEMPTIMG normal BUY for',round(price,2))
            g = Gambit(portfolio, symbol, price, qty, 'buy')
        case 'BB':
            print('\tATTEMPTIMG BIG BUY for',round(price,2))
            g = Gambit(portfolio, symbol, price, qty, 'buy',gb.LIVE_BUFFER*2)

def enter_short_commands(command, portfolio, symbol, qty, price):
    match command:
        case 's':
            print('\tATTEMPTIMG little SHORTSELL for',round(price,2))
            g = Gambit(portfolio, symbol, price, qty, 'shortsell', buffer=gb.S_LIVE_BUFFER)
        case 'S':
            print('\tATTEMPTIMG normal SHORTSELL for',round(price,2))
            g = Gambit(portfolio, symbol, price, qty, 'shortsell')
        case 'SS':
            print('\tATTEMPTIMG BIG SHORTSELL for',round(price,2))
            g = Gambit(portfolio, symbol, price, qty, 'shortsell', buffer=gb.LIVE_BUFFER*2)

def exit_commands(command, portfolio, symbol, price):
    qty = portfolio.get_qty(symbol)
    side = 'shortbuy' if qty < 0 else 'sell'
    g = None
    match command:
        case 'C':
            print('\tATTEMPTIMG normal CLEAR for', round(price,2))
            g = Gambit(portfolio, symbol, price, portfolio.get_qty(symbol), side)
        case 'c':
            print('\tATTEMPTIMG little CLEAR for', round(price,2))
            g = Gambit(portfolio, symbol, price, portfolio.get_qty(symbol), side, buffer=gb.S_LIVE_BUFFER)
        case 'CC':
            print('\tATTEMPTIMG BIG CLEAR for', round(price,2))
            g = Gambit(portfolio, symbol, price, portfolio.get_qty(symbol), side, buffer=gb.LIVE_BUFFER*2)
    if g and hasattr(g, 'profit'): print('\n'+'='*30+'\t\t\t\nOUR PROFIT WAS '+str(round(g.profit,2))+'\n'+'='*30)

def piecemeal_trader(symbol, qty, portfolio):
    while True:
        print("\nNEW TRADE")
        # try:
        if not portfolio.has_stock(symbol):
            print("\tNO STOCK FOUND: Buy or Shortsell (b/s)")
            command = input('\tBuy or Sell (b/s): ')
            price = get_alp_price(api, symbol)
            if not price: print('PRICE NOT FOUND'); continue
            enter_long_commands(command, portfolio, symbol, qty, price)
            enter_short_commands(command, portfolio, symbol, qty, price)

        # Long Position
        elif portfolio.get_stock_sign(symbol):
            print("\tLONG FOUND, Clear? (c), or Buy (b)\n\tCURRENT QTY IS:",portfolio.get_qty(symbol))
            command = input("LONG FOUND, Clear? (c), or Buy (b): ")
            price = get_alp_price(api, symbol)
            if not price: print('PRICE NOT FOUND'); continue
            exit_commands(command, portfolio, symbol, price)
            enter_long_commands(command, portfolio, symbol, qty, price)

        # Short Position
        else:
            print("\tSHORT FOUND, Clear? (c), or Sell (s)\n\tCURRENT QTY IS:",portfolio.get_qty(symbol))
            command = input("SHORT FOUND, Clear? (c), or Sell (s): ")
            price = get_alp_price(api, symbol)
            if not price: print('PRICE NOT FOUND'); continue
            exit_commands(command, portfolio, symbol, price)
            enter_short_commands(command, portfolio, symbol, qty, price)

piecemeal_trader(symbol, qty, portfolio)