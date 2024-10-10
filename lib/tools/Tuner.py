import sys; sys.path.append('../lib/*/*'); sys.path.append('..')
import lib.tools.Toolbox as tb
import lib.tools.TimeKeeper as tk
import metadata.trade_configs.Globals as gb
import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as pta
import lib.tools.Broker as Broker
import lib.tools.Scrivener as sc
import lib.tools.Logger as log
import glob
import os.path as p
from lib.tools.Config import Config
from lib.Portfolio import Portfolio
from lib.RoboTrader import RoboTrader
from lib.strategies.MomentumSeeking import MomentumSeeking
from lib.selectors.SimpleSelection import SimpleSelection
from lib.selectors.TuningSelection import TuningSelection


def tuning(lookback_days = -1, logging:bool = False, show:bool = False, allow_output:bool = True, selector=SimpleSelection, strategy=MomentumSeeking, s:pd.Timestamp = None, e:pd.Timestamp = None, keep_history:bool = False, banned_dates:list = [], sconfs:dict = {}, symbols = []):
    '''Runs a stock experiment on the given range of days. Days should be a negative number for how far back you want to look'''
    if allow_output: print(tb.logo())

    log.ENABLE_LOGGING = logging
    if isinstance(symbols, str): symbols = [symbols]
    
    if isinstance(lookback_days, pd.Timestamp): dates = [lookback_days]
    elif isinstance(lookback_days, list): dates = lookback_days
    elif s and not e:
        dates = pd.date_range(start=s, end=tk.today(), freq='B')
        dates = dates[lookback_days:] if tk.is_after(gb.TRADE_START_HOUR, gb.TRADE_START_MINUTE, tk.now()) else dates[lookback_days-1:len(dates)-1]
    elif s and e:
        dates = pd.date_range(start=s, end=e, freq='B')
    else:
        dates = pd.date_range(start=tk.today()-pd.DateOffset(days=abs(lookback_days*3)), end=tk.today(), freq='B')
        dates = dates[lookback_days:] if tk.is_after(gb.TRADE_START_HOUR, gb.TRADE_START_MINUTE, tk.now()) else dates[lookback_days-1:len(dates)-1]
    conf, final_total = Config('base'), 0
    profit_tally = {key:0 for key in symbols} if symbols else {key:0 for key in sc.load_symbols()}
    success, failure = [], []

    results = []
    if allow_output: print('Dates Covered\n',dates)
    previous_amount= 100000
    for date in dates:
        if date in banned_dates: print(date,'banned by order of the Department of Normalcy'); continue
        #if date.weekday() == 1: continue
        trader = RoboTrader(None, conf, selector=selector, strategy=strategy, symbols=symbols)
        if keep_history: trader.port.cash = previous_amount
        for symbol in symbols: log.clear_logs(None, date, symbol)
        try:
            if not sconfs: tickers = trader.trade_simulation(date, starting_capital=previous_amount)
            else: tickers = trader.trade_simulation(date, sconfs, starting_capital=previous_amount)
        #except FileNotFoundError: print('skipping',date); continue
        except sc.HolidayException: print('Attempted Trade on a Holiday on', date); continue
        except RoboTrader.NoProfitableSymbolsException: print('No symbols were Worth Trading on', date); continue
        # except KeyError: print('AHHH'); continue
        # except ConnectionError: print('Alpaca is sleeping today')
        #tickers = trader.trade_simulation(date)
        day_profit = trader.port.cash-previous_amount
        if keep_history:
            previous_amount+=day_profit*4
            #previous_amount+=day_profit
        if show:
            for ticker in tickers: tickers[ticker].plot_line()
            
        results.append({'date':date, 'profit': day_profit})

        if allow_output:
            string = str(date.month)+'/'+str(date.day) +' '+ str(date.day_name())+' '+ str(round(day_profit,2))+'\t\t'+str(round(final_total,2))
            if len(trader.bulls) == 1: string+='\tleast_value: '+str(list(trader.strategies.values())[0].least_value)
            print(string)
            if len(trader.bulls) > 1:
                for symbol in trader.bulls:
                    profit_tally[symbol] += tickers[symbol].ticker_profit
                    print('\t'+symbol+':',round(trader.strategies[symbol].ticker_profit,2))

        final_total += day_profit
    if len(results) == 0: return
    results = pd.DataFrame(results); results.set_index('date', inplace=True)

    if allow_output:
        print('\nTOTAL:',round(results.profit.sum(),2), '\nDAILY:',
      round(results.profit.mean(),2), 'over',len(results),'days')
        if len(results.profit[results.profit < 0]) > 0:
            print('\tAverage Loss:',round(results.profit[results.profit < 0].mean(),2),
        '\n\tTotal Losses:',round(results.profit[results.profit < 0].sum(),2),
        '\n\tGreatest Loss in a Day',round(results.profit[results.profit < 0].min()))
    
    if allow_output:
        print('Profits by Symbol')
        for ticker in profit_tally: print('\t',ticker+':',profit_tally[ticker])
    return results

def compound_tuning():
    ''' Function which measures compound tuning technique. I.e performs parameter tuning every monday to attempt to check best
        best parameters for the given day based on the last 7 days of behavior.
    '''
    ''