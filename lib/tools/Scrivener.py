import metadata.trade_configs.Globals as gb
from slack_sdk.errors import SlackApiError
import lib.tools.Broker as br
import lib.tools.TimeKeeper as tk
import lib.tools.Toolbox as tb
import lib.tools.Logger as log
import alpaca_trade_api as alp
import numpy as np
import pandas as pd
from scipy import stats
import os
from os import path as p
import pytz
import glob

client, logger, channel_id = br.slack_client()

def update_archive(symbol:str, date:pd.DatetimeIndex = tk.today(), pips:list = [gb.PIP_DURATION], api:alp.REST = None):
    '''Foundational method. Attempts to update our archives for the given symbol for the given day'''
    if not bool(len(pd.bdate_range(date, date))): return None
    datas, symbol = {}, symbol.upper()
    for pip in pips:
        if isinstance(pip, list): pip, lookback = pip
        else: lookback = 0

        datename = f'{pip}_{date.strftime("%Y-%m-%d")}'; ppath = f'../stock_archive/bars/{symbol}'
        if not p.isdir(ppath): os.makedirs(ppath)
        if not p.isfile(f'{ppath}/{datename}.pkl'): data = get_days_bars(symbol, date, pip, api)
        else: data = pd.read_pickle(f'{ppath}/{datename}.pkl')
        if not data.index[-1] == tk.get_market_close(date):
            data = easy_concat(data, get_bars(symbol, data.index[-1], tk.get_market_close(date), api=api))
            data.to_pickle(f'{ppath}/{datename}.pkl')
        if lookback > 0: data = easy_concat(get_last_day_bars(symbol, date, lookback, pip, api), data)
        datas[pip] = data
    return datas

def get_bars(symbol:str, s:pd.DatetimeIndex, e:pd.DatetimeIndex, pip:alp.TimeFrame = alp.TimeFrame.Minute, api:alp.REST = None):
    '''Functions as api.get_trades() except converts to a df with price and size and can handle datetime objects'''
    if not api: api = br.paper_api()
    if not isinstance(s, str): s = tk.dto_time(s)
    if not isinstance(e, str): e = tk.dto_time(e)
    # print('Pulling bars from',s,'to',e)
    bars = api.get_bars(symbol.upper(), timeframe=pip, start=s, end=e).df
    if len(bars) == 0: return None
    bars.index = bars.index.tz_convert(pytz.timezone('America/New_York'))
    return bars

def get_bar(symbol:str, api:alp.REST):
    '''Get's the last minute of the symbol and waits if it doesn't match'''
    pip = tk.now().round('min')
    bars = get_bars(symbol, pip-pd.DateOffset(minutes=3), pip, api=api)
    return bars.iloc[-3:]

def get_days_bars(symbol:str, date:pd.DatetimeIndex = tk.today(), pip:alp.TimeFrame = alp.TimeFrame.Minute, api:alp.REST = None):
    '''Returns the trades of just today'''
    try:
        return get_bars(symbol.upper(), tk.get_market_open(date), tk.get_market_close(date), pip, api=api)[tk.get_market_open(date):]
    except TypeError:
        raise HolidayException

def construct_archive(symbol:str, start_date:pd.Timestamp = None):
    '''Constructs an archive for the given symbol. Can input Timestamp or integer for start_date. If integer then looks back
        that many business days and pulls.
    '''
    api = br.paper_api()
    if isinstance(start_date, pd.Timestamp): drange = pd.date_range(start=start_date, end=tk.today(), freq='B')
    elif isinstance(start_date, int): drange = pd.date_range(start=tk.today()-pd.DateOffset(days=abs(start_date)), end=tk.today(), freq='B')
    else: drange = [tk.today()]
    for date in drange:
        try: update_archive(symbol.upper(), date, api)
        except Exception as e: print(date,'failed to pull, no date') 
        
def update_tracked_archives():
    for symbol in tb.get_symbols('tracked_tickers.txt'): construct_archive(symbol.upper())

def get_archive(symbol:str, date:pd.DatetimeIndex = None, pip:int = gb.PIP_DURATION, api:alp.REST = None):
    '''Retrieves an archive of minute data from our stores and returns it as a normal datasource'''
    archive, symbol = None, symbol.upper()
    if isinstance(date, pd.Timestamp): dates = [date]
    elif not date: dates = [tk.today()]
    elif isinstance(date, list): dates = date
    else: dates = [pd.to_datetime(p.basename(l).split('_')[1].strip('.pkl')) for l in glob.glob(p.join('../stock_archive','bars',symbol+'/'+str(pip)+'_*'))]
    for date in dates:
        name = str(pip)+'_'+date.strftime("%Y-%m-%d")+'.pkl'
        archive_path = p.join('..','stock_archive','bars',symbol,name)
        if not p.isfile(archive_path): update_archive(symbol, date, [pip], api)[pip].to_pickle(archive_path)
        archive = pd.read_pickle(archive_path)
    return archive

def get_archives(symbol:str, date:pd.DatetimeIndex = None, pips:list = [gb.PIP_DURATION], api:alp.REST = None):
    '''Returns the archives for each pip, including lookbacks'''
    archives, symbol = {}, symbol.upper()
    for pip in pips:
        if isinstance(pip, list): pip, lookback = pip
        else: lookback = 0
        archive = get_archive(symbol, date, pip)
        if lookback > 0: archive = easy_concat(get_last_day_bars(symbol, date, lookback, pip, api), archive)
        archives[pip] = archive
    return archives

def get_last_day_bars(symbol:str, date:pd.Timestamp, lookback:int = 1, pip:int = gb.PIP_DURATION, api:alp.REST = None):
    '''Returns the df of the last trading day for the given symbol. If lookback is greater than one then will try to add even more data'''
    drange, df, symbol = pd.date_range(start=date-pd.DateOffset(days=4+lookback), end=date-pd.DateOffset(days=1), freq='B'), [], symbol.upper()
    for date in reversed(drange):
        try:
            if not len(df): df = list(update_archive(symbol, date, [pip], api).values())[0]
            elif lookback > 1: df = easy_concat(list(update_archive(symbol, date, [pip], api).values())[0], df); lookback -= 1
            else: break
        except: '''No data today, likely holiday'''
    return df

def update_trades(symbol:str, date:pd.DatetimeIndex = tk.today(), api:alp.REST = None):
    '''Updates the trade info of the given day for the given symbol'''
    datename = date.strftime("%Y-%m-%d"); rpath = f'../stock_archive/raw/{symbol}'
    if not p.isdir(rpath): os.makedirs(rpath)
    if not p.isfile(f'{rpath}/{datename}.pkl'): get_days_trades(symbol, date, api=api).to_pickle(f'{rpath}/{datename}.pkl')
    trades = pd.read_pickle(f'{rpath}/{datename}.pkl')
    if trades.index[-1].round('s') == tk.get_market_close(date): return trades
    trades = easy_concat(trades, get_trades(symbol, trades.index[-1], tk.get_market_close(date), api=api))
    trades.to_pickle(f'{rpath}/{datename}.pkl')
    return trades

def get_trades(symbol:str, s:pd.DatetimeIndex, e:pd.DatetimeIndex, api:alp.REST = None):
    '''Functions as api.get_trades() except converts to a df with price and size and can handle datetime objects'''
    if not api: api = br.paper_api()
    if not isinstance(s, str): s = tk.dto_time(s)
    if not isinstance(e, str): e = tk.dto_time(e)
    print('Pulling trades from',s,'to',e)
    trades = api.get_trades(symbol, start=s, end=e).df
    if len(trades) == 0: return None
    trades.index = trades.index.tz_convert(pytz.timezone('America/New_York'))
    return trades[['price','size']]

def get_days_trades(symbol:str, date:pd.DatetimeIndex = tk.today(), api:alp.REST = None):
    '''Returns the trades of just today'''
    return get_trades(symbol, tk.get_market_open(date), tk.get_market_close(date), api=api)[tk.get_market_open(date):]

def construct_archive(symbol:str, start_date:pd.Timestamp = None):
    '''Constructs an archive for the given symbol. Can input Timestamp or integer for start_date. If integer then looks back
        that many business days and pulls.
    '''
    api = br.paper_api()
    if isinstance(start_date, pd.Timestamp): drange = pd.date_range(start=start_date, end=tk.today(), freq='B')
    elif isinstance(start_date, int): drange = pd.date_range(start=tk.today()-pd.DateOffset(days=abs(start_date)), end=tk.today(), freq='B')
    else: drange = [tk.today()]
    for date in drange:
        try: update_archive(symbol, date, api)
        except Exception as e: print(date,'failed to pull, no date') 
        
def update_tracked_archives():
    for symbol in tb.get_symbols('tracked_tickers.txt'): construct_archive(symbol)

def get_trade_archive(symbol:str, date:pd.DatetimeIndex = None):
    '''Returns the trades from the given date/dates'''
    archive = None
    if isinstance(date, pd.Timestamp): dates = [date]
    elif not date: dates = [tk.today()]
    elif isinstance(date, list): dates = date
    else: [pd.to_datetime(p.basename(l).split('_')[1].strip('.pkl')) for l in glob.glob(p.join('../stock_archive','raw',symbol.upper()+'/*'))]
    for date in dates:
        name = date.strftime("%Y-%m-%d")+'.pkl'
        archive_path = p.join('..','stock_archive','raw',symbol.upper(),name)
        if not p.isfile(archive_path): archive_path = p.join('..',archive_path)
        archive_day = pd.read_pickle(archive_path)
        archive = easy_concat(archive, archive_day) if isinstance(archive, pd.DataFrame) else archive_day
    return archive

def get_last_trading_day(symbol:str, date:pd.Timestamp, lookback:int = 1, pip:int = gb.PIP_DURATION):
    '''Returns the df of the last trading day for the given symbol. If lookback is greater than one then will try to add even more data'''
    drange, df = pd.date_range(start=date-pd.DateOffset(days=4+lookback), end=date-pd.DateOffset(days=1), freq='B'), []
    for date in reversed(drange):
        try:
            if not len(df): df = get_archive(symbol, date, pip)
            elif lookback > 1: df = easy_concat(get_archive(symbol, date, pip), df); lookback -= 1
        except: '''No data today, likely holiday'''
    return df

def easy_concat(df1:pd.DataFrame, df2:pd.DataFrame):
    '''Quick and dirty wrapper method to concat two dataframes and remove duplicates'''
    df = pd.concat([df1,df2])
    df = df[~df.index.duplicated(keep='last')]
    return df.sort_index()

def compare_logs(symbol:str, date:pd.DatetimeIndex = tk.today()):
    bops, bords, tops, tords, symbol = log.get_log(symbol, date, 'brokerage', 'ops'), log.get_log(symbol, date, 'brokerage', 'orders'), log.get_log(symbol, date, 'training', 'ops'), log.get_log(symbol, date, 'training', 'orders'), symbol.upper()
    
    print('Searching for Discrepency in OPERATIONS')
    for index in bops.index:
        if index in tops.index:
            be, te = bops.loc[index], tops.loc[index]
            if be.close==te.close and be.bollinger_high and te.bollinger_high and be.volume == te.volume:
                continue
            print(index, 'DISCREPENCY')
            
    print('Searching for Discrepency in ORDERS')
    for index in bords.index:
        if index in tords.index:
            be = bords.loc[index] if len(bords.loc[index]) > 2 else bords.loc[index].iloc[0]
            te = tords.loc[index]
            if be.status == 'uninitialized': continue
            if be.side == te.side:
                continue
            print(index, 'DISCREPENCY', be, te)

def load_symbols(filename:str = 'active_symbols'):
    symbols, filename = [], filename+'.txt' if '.txt' not in filename else filename
    path = './metadata/symbol_lists/'+filename if p.isfile('./metadata/symbol_lists/'+filename) else '../metadata/symbol_lists/'+filename
    with open(path, 'r') as f:
        for symbol in f.read().split('\n'): symbols.append(symbol)
    return symbols

def post_to_slack(msg:str):
    '''Posts the message to slack and prints it to terminal'''
    # ID of channel you want to post message to
    print(msg)

    if client:
        try:
            # Call the conversations.list method using the WebClient
            result = client.chat_postMessage(
                channel=channel_id,
                text=msg
                # You could also use a blocks[] array to send richer content
            )
            # Print result, which includes information about the message (like TS)

        except SlackApiError as e:
            print(f"Error: {e}")

class HolidayException(Exception):
    pass