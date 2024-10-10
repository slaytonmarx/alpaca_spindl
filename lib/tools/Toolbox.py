# Set of Universal Tools for problems that keep popping up.

import sys; sys.path.append('../..'); sys.path.append('..')
from scipy.signal import argrelextrema
import pandas_ta as pta
import pandas as pd
import os.path as p
import lib.tools.Broker as br
import numpy as np
import lib.tools.TimeKeeper as tk
import pytz
import alpaca_trade_api as alp
import subprocess as sub
import matplotlib.pyplot as plt
import metadata.trade_configs.Globals as gb
from collections import deque
import pandas as pd
from scipy import stats

def get_i(index:pd.DatetimeIndex, data:pd.DataFrame):
    '''Returns the i of the nearest index in a DataFrame to the given index'''
    if type(index) == str: print('You are passing the column names, make sure to add .index')
    return data.index.get_indexer([index], method='nearest')[0]

def get_index(index:pd.DatetimeIndex, data:pd.DataFrame):
    '''Returns the nearest index in a DataFrame to the given index. IMPORTANT: Gets the index itself, not just the i of the index'''
    return data.index[get_i(index, data)]

def get_previous_index(index:pd.DatetimeIndex, data:pd.DataFrame, offset:int = 1):
    '''Returns the nearest index in a DataFrame to the given index, minus an offset.'''
    return data.index[get_i(index, data)-offset]

def normalize_column(series:pd.Series, set_unit:bool=False):
    '''Normalizes the values of a series'''
    ma,mi = series.max(), series.min()
    if set_unit: series.index=range(len(series))
    return (series-mi)/(ma-mi)

def unnormalize_column(series:pd.Series, unnorm_factor:pd.Series):
    '''Unnormalizes the values of a normalized series by the max and min of another series'''
    ma,mi = unnorm_factor.max(), unnorm_factor.min()
    return series*(ma-mi)+mi

def get_trend(index:pd.DatetimeIndex, series:pd.Series, ema:pd.Series):
    '''Returns the trend of the data given the ema'''
    ema_slope = ema[:index].tail(2).diff().mean() > 0
    value_placement = series.loc[index] > ema.loc[index]
    if ema_slope and value_placement: return 1
    elif not ema_slope and not value_placement: return -1
    else: return 0
        
def get_trend_fit(data:pd.Series, norm_factor:int = 0):
    '''Takes a portion of data and reports whether that data is on an up trend or a down trend'''
    trends = [[],[]]
    if norm_factor: data = data.ewm(span=norm_factor).mean()
    workday_length = len(data)
    for i in [1,-1]:
        series = trends[0] if i == 1 else trends[1]
        for j in range(workday_length):
            value = round(1/workday_length*j*i,3)
            if i == -1: value += 1
            series.append(value)
    pos_trend, neg_trend = pd.Series(trends[0], dtype=float), pd.Series(trends[1], dtype=float)
    normed = normalize_column(data, True)
    pos_score, neg_score = abs(normed - pos_trend).mean(), abs(normed - neg_trend).mean()
    return -(pos_score - neg_score)

def get_ups_and_downs_by_trend(fine_data:pd.DataFrame, threshold:float = .2):
    '''A function that is shockingly common (enough so to finally move it to toolbox). Finds the up
        and down days for a span of data (only the fine_data, though it's smart enough that you can)
        give it however much mo_data you want). For threshold, standard is .2, less means a wider net.
    '''
    ups, downs = [], []
    for day in get_unique_dates(fine_data):
        data = tk.get_workday(fine_data, day)
        upness = get_trend_fit(data.open)
        if upness < -threshold: ups.append(day)
        elif upness > threshold: downs.append(day)
    return [ups, downs]

def fractionate_data(data:pd.DataFrame, factor:int, column:str = 'open'):
    '''Takes the given data and returns a data frame divided by the given factor (so 5 would be 5 minutes, 60 would be by the hour)'''
    fractionated_data = []
    for index in data.index:
        if index.minute % factor == 0:
            window = data[index:index+pd.DateOffset(minutes=factor-1)]
            fractionated_data.append({'index':index, 'low':window[column].min(), 'high':window[column].max(), 'open':window[column].iloc[0], 'close':window[column].iloc[-1]})
    df = pd.DataFrame(fractionated_data)
    df.set_index('index', inplace=True)
    df = df.sort_index().drop_duplicates()
    return df

def quick_fractionate(data:pd.DataFrame, s_i:int, factor:int):
    '''Fractionates the data assuming we will want to have only the open values for our work. S_i is the start point for the day in question.
        Works by taking a start point and backfilling our fractionated data from it (thus resolving the 60, 6.5 paradox)
    '''
    df = []
    absolute_start_i = len(data.index[:s_i]) - int(len(data.index[:s_i])/factor)*factor

    # Backfill
    for i in range(absolute_start_i, len(data.index[:s_i]), factor):
        df.append({'i':i, 'date':data.index[i],'open':data.open.iloc[i]})
    # Frontfill
    for i in range(s_i, s_i + len(data[data.index[s_i]:data.index[s_i]+pd.DateOffset(days=1)]), factor):
        #if i == s_i: continue
        df.append({'i':i, 'date':data.index[i],'open':data.open.iloc[i]})
    df = pd.DataFrame(df)
    df.set_index('date',inplace=True)
    return df

def get_percentile(series:pd.Series, point:float):
    '''Checks the percentile of the given data point compared to it's surrounding data'''
    high, low = series.quantile(.01), series.quantile(.99)
    if point > high: return 1
    elif point < low: return -1
    else: return 0

def get_haiken_ashi(df:pd.DataFrame):
    '''Returns the data in averaged, haiken ashi form'''
    cl = (df.open+ df.high+ df.low + df.close)/4
 
    op = df.open.copy()
    for i in range(0, len(df)):
        if i == 0:
            op.iloc[i]= ( (df.open.iloc[i] + df.close.iloc[i] )/ 2)
        else:
            op.iloc[i] = ( (op.iloc[i-1] + cl.iloc[i-1] )/ 2)
 
    #hi=df[['open','close','high']].max(axis=1)
    #lo=df[['open','close','low']].min(axis=1)
    hi, lo = df.high, df.low
    ha = pd.concat([op, cl, lo, hi], axis=1)
    ha.columns=['open','close','low','high']
    return ha

def get_parabolic_sar(data:pd.DataFrame):
    '''Returns the parabolic sar for the given data'''
    indic = PSAR()
    psar = data.apply(lambda x: indic.calcPSAR(x['high'], x['low']), axis=1)
    # Add supporting data
    #data['ep'] = indic.ep_list
    #data['trend'] = indic.trend_list
    #data['af'] = indic.af_list
    return psar

def get_macd(data:pd.DataFrame, short:int, long:int, signal:int):
    '''Returns the data with the macd values for the given parameters added as columns'''
    data = data.copy()
    k = data['open'].ewm(span=short, adjust=False, min_periods=short).mean()
    d = data['open'].ewm(span=long, adjust=False, min_periods=long).mean()
    data['macd'] = k - d
    data['macd_s'] = data.macd.ewm(span=signal, adjust=False, min_periods=signal).mean()
    data['macd_h'] = data.macd - data.macd_s
    data['macd_hd'] = data.macd_h.diff()
    data['macd_ha'] = data.macd_hd.diff()
    return data

def get_macd_crossing_points(data:pd.DataFrame):
    '''Finds the points where macd crosses from positive to negative and negative to positive.
        This is a common enough thing in data analysis that I'm just going to write this here
        for use later.
    '''
    ups, downs = [], []
    for index in data.index:
        if index == data.index[0]: continue
        last_index = get_previous_index(index, data, 1)
        if data.macd_h.loc[index] > 0 and data.macd_h.loc[last_index] < 0: ups.append(index)
        elif data.macd_h.loc[index] < 0 and data.macd_h.loc[last_index] > 0: downs.append(index)
    return [ups, downs]

def get_rsi(data:pd.DataFrame, period:int = 14, column:str = 'open'):
    '''Adds the rsi value to the data and returns it'''
    delta = data[column].diff()
    delta.dropna(inplace=True)

    delta_pos = delta.copy(); delta_pos[delta_pos<0] = 0
    delta_neg = delta.copy(); delta_neg[delta_neg>0] = 0

    delta.equals(delta_pos+delta_neg)

    avg_up = delta_pos.rolling(period).mean()
    avg_down = delta_neg.rolling(period).mean().abs()
    avg_up.dropna(inplace=True)
    avg_down.dropna(inplace=True)
    
    return (100 * avg_up / (avg_up + avg_down))#.ewm(span=3).mean()

def get_obv(data:pd.DataFrame):
    '''Returns the OBV for the given data'''
    return (np.sign(data.open.diff()) * data.volume).fillna(0).cumsum()

def get_atr(data:pd.DataFrame, window=14):
    '''Returns the atr for the given data'''
    return pta.atr(data.high, data.low, data.close, window=window, fillna=0)

def get_atr_piecemeal(data:pd.DataFrame, index:pd.DatetimeIndex):
        return get_atr(data[index-pd.DateOffset(seconds=15*60):index]).iloc[-1]

def get_bollinger_bands(series: pd.Series, length: int = 20, *, num_stds: tuple[float, ...] = (2, 0, -2), prefix: str = '') -> pd.DataFrame:
    '''Returns a dataframe with the bollinger bands'''
    rolling = series.rolling(length)
    bband0 = rolling.mean()
    bband_std = rolling.std(ddof=0)
    std_name = {num_stds[0]:'highband',num_stds[1]:'moving_average',num_stds[2]:'lowband'}
    return pd.DataFrame({f'{prefix}{std_name[num_std]}': (bband0 + (bband_std * num_std)) for num_std in num_stds})

def get_keltner_bands(data:pd.DataFrame, window:int = 20, kc_mult:int = 2):
    # first we need to calculate True Range
    m_avg, mult_KC = data.close.rolling(window=window).mean(), kc_mult
    # first we need to calculate True Range
    tr0 = abs(data.high - data.low)
    tr1 = abs(data.high - data.close.shift())
    tr2 = abs(data.low - data.close.shift())
    tr = pd.concat([tr0, tr1, tr2], axis=1).max(axis=1)
    # moving average of the TR
    range_ma = tr.rolling(window=window).mean()

    # upper Keltner Channel
    upper_KC = m_avg + range_ma * mult_KC
    # lower Keltner Channel
    lower_KC = m_avg - range_ma * mult_KC

    return pd.DataFrame({'upperKC': upper_KC, 'lowerKC': lower_KC})

def get_keltner_piecemeal(data:pd.DataFrame, window:int = 20, kc_mult:int = 1):
    '''Returns the Keltner band values purely for this latest i with the least possible compute necessary'''
    if len(data) < window - 1: print('Keltner band needs to at least be 1 minus the length, in this case', window-1); return None
    return get_keltner_bands(data.iloc[-20:], window, kc_mult)

def get_squeeze_momentum(data:pd.DataFrame, keltner:pd.DataFrame, bollinger:pd.DataFrame, length_kc:int = 20, min_squeeze:int = 6, offset:bool = False):
    '''Attempts to get the squeeze momentum data for the given ranges.'''
    #keltner = keltner.iloc[-len(bollinger):]
    squeeze_on = (bollinger.lowband > keltner.lowerKC) & (bollinger.highband < keltner.upperKC)
    #squeeze_off = (bollinger.lowband < keltner.lowerKC) & (bollinger.highband > keltner.upperKC)
    m_avg = data.close.rolling(window=length_kc).mean()

    # calculate bar value
    highest = data.high.rolling(window = length_kc).max()
    lowest = data.low.rolling(window = length_kc).min()
    m1 = (highest + lowest)/2
    value = (data.close - (m1 + m_avg)/2)
    vdiff = value.diff()
    fit_y = np.array(range(0,length_kc))
    value = value.rolling(window = length_kc).apply(lambda x: 
                            np.polyfit(fit_y, x, 1)[0] * (length_kc-1) + 
                            np.polyfit(fit_y, x, 1)[1], raw=True)

    # buying window for long position:
    long_squeeze = (squeeze_on.rolling(min_squeeze).sum()==min_squeeze).shift().shift()
    # 1. black cross becomes gray (the squeeze is released)
    squeeze_released = ((squeeze_on.shift() == True) & (squeeze_on == False)) if not offset else ((squeeze_on.shift(2) == True) & (squeeze_on.shift() == False) & (squeeze_on == False))

    # 2. bar value is positive => the bar is light green k

    long_cond2 = value > 0
    enter_long = (squeeze_released & long_cond2) & long_squeeze

    # buying window for short position:
    # 1. black cross becomes gray (the squeeze is released)
    # 2. bar value is negative => the bar is light red 

    short_cond2 = value < 0
    enter_short = (squeeze_released & short_cond2) & long_squeeze

    squeeze = pd.concat([enter_long, enter_short, value, vdiff, squeeze_released, long_squeeze, squeeze_on], axis=1)
    squeeze.columns=['enter_long','enter_short', 'value', 'vdiff', 'squeeze_released', 'long_squeeze', 'squeeze_on']

    return squeeze

def check_bollinger(index:pd.DatetimeIndex, data:pd.DataFrame, bollinger:pd.DataFrame, full_signals:bool = False, column:str = 'open'):
    '''Checks whether the given index counts as a bollinger event'''
    if type(index) == int:
        try:
            if index >= len(data): index = len(data) - 1
            pindex = index-1
            val, pval, bol, pbol = data[column].iloc[index], data[column].iloc[pindex], bollinger.iloc[index], bollinger.iloc[pindex]
        except:
            print('Check Bollinger Failure')
            print(index, len(data))
    else:
        pindex = get_previous_index(index, data)
        val, pval, bol, pbol = data[column].loc[index], data[column].loc[pindex], bollinger.loc[index], bollinger.loc[pindex]

    if val > bol.lowband and pval < pbol.lowband: return 1
    elif val < bol.highband and pval > pbol.highband: return -1
    if full_signals:
        if val > bol.highband and pval < pbol.highband: return 2
        elif val < bol.lowband and pval > pbol.lowband: return -2
    return 0

def plot_data_and_bollinger(data:pd.DataFrame, bollinger:pd.DataFrame, sales:list = []):
    '''Plots a data graph and it's associated bollinger bands'''
    plt.figure(dpi=200)
    plt.plot(data.index, data.open, lw=.5)
    plt.plot(bollinger.index, bollinger.highband, color='green', lw=.5)
    plt.plot(bollinger.index, bollinger.moving_average, color='green', lw=.5)
    plt.plot(bollinger.index, bollinger.lowband, color='red', lw=.5)
        
def get_bollinger_piecemeal(series:pd.Series, bol_length:int = 20, bol_dev:float = 1):
    '''Returns the bollinger bands of the latest entry in the data purely based on said data'''
    if len(series) < bol_length: print('Insufficient length for bollinger'); return pd.DataFrame([{}])
    elif len(series) > bol_length+1: series = series.iloc[-bol_length:]
    #print('Bollinger input greater than necessary by', len(series)-bol_length-1)
    rolling = series.rolling(bol_length)
    bband0 = rolling.mean()
    bband_std = rolling.std(ddof=0)
    num_stds = (bol_dev, -bol_dev)
    std_name = {num_stds[0]:'highband',num_stds[1]:'lowband'}
    return pd.DataFrame({f'{std_name[num_std]}': (bband0 + (bband_std * num_std)) for num_std in num_stds}).iloc[-2:]

def get_macd_piecemeal(series:pd.Series, long:int = 26, short:int = 12, signal:int = 9):
    '''Returns the macd of the latest entry in the data given'''
    if len(series) < long+signal-1: print('Insufficient length for macd (needs long+signal-1)'); return pd.DataFrame([{}])
    k = series.ewm(span=short, adjust=False, min_periods=short).mean()
    d = series.ewm(span=long, adjust=False, min_periods=long).mean()
    macd = k - d
    macd_s = macd.ewm(span=signal, adjust=False, min_periods=signal).mean()
    macd_h = macd - macd_s
    return macd_h.iloc[-1]

def backfill_data(data:pd.DataFrame):
    '''Backfills any missing entries in incomming minute data'''
    for i in range(len(data.index))[:-1]:
        step = data.index[i]
        next_step = data.index[i+1]
        difference = next_step - step
        if difference < pd.Timedelta(hours=3) and difference > pd.Timedelta(minutes=1):
            #print(step, 'DIFFERENCE DISCOVERED OF ',difference)
            minutes_to_fill = difference.seconds/60
            for j in range(1,int(minutes_to_fill)):
                data.loc[step+pd.DateOffset(minutes=j)] = data.loc[step]
    data.sort_index(inplace=True)
    return data
        
def get_unique_dates(data:pd.DataFrame):
    '''Returns a series of the unique days within a datetime index'''
    return pd.to_datetime(data.index).normalize().unique()

def get_local_maxima_and_minima(series:pd.Series, index:pd.DatetimeIndex = None):
    '''Returns two lists of the local maxima and minima'''
    n, index = 5, series.index[-1] if not index else index
    maxima = series.iloc[argrelextrema(series[:index].values, np.greater_equal, order=n)[0]]
    minima = series.iloc[argrelextrema(series[:index].values, np.less_equal, order=n)[0]]
    return maxima, minima

def get_ema(arr, periods=14, weight=1, init=None):
    leading_na = np.where(~np.isnan(arr))[0][0]
    arr = arr[leading_na:]
    alpha = weight / (periods + (weight-1))
    alpha_rev = 1 - alpha
    n = arr.shape[0]
    pows = alpha_rev**(np.arange(n+1))
    out1 = np.array([])
    if 0 in pows:
        out1 = get_ema(arr[:int(len(arr)/2)], periods)
        arr = arr[int(len(arr)/2) - 1:]
        init = out1[-1]
        n = arr.shape[0]
        pows = alpha_rev**(np.arange(n+1))
    scale_arr = 1/pows[:-1]
    if init:
        offset = init * pows[1:]
    else:
        offset = arr.iloc[0]*pows[1:]
    pw0 = alpha*alpha_rev**(n-1)
    mult = arr*pw0*scale_arr
    cumsums = mult.cumsum()
    out = offset + cumsums*scale_arr[::-1]
    out = out[1:] if len(out1) > 0 else out
    out = np.concatenate([out1, out])
    out[:periods] = np.nan
    out = np.concatenate(([np.nan]*leading_na, out))
    out = pd.Series(out)
    out.index = arr.index
    return out

def get_adx(df:pd.DataFrame, periods=14):
    highs = np.array(df.high)
    lows = np.array(df.low)
    up = highs[1:] - highs[:-1]
    down = lows[:-1] - lows[1:]
    up_idx = up > down
    down_idx = down > up
    updm = np.zeros(len(up))
    updm[up_idx] = up[up_idx]
    updm[updm < 0] = 0
    downdm = np.zeros(len(down))
    downdm[down_idx] = down[down_idx]
    downdm[downdm < 0] = 0
    _atr = get_atr(df)[1:]
    updi = 100 * get_ema(updm, periods) / _atr
    downdi = 100 * get_ema(downdm, periods) / _atr
    zeros = (updi + downdi == 0)
    downdi[zeros] = .0000001
    adx = 100 * np.abs(updi - downdi) / (updi + downdi)
    adx = get_ema(np.concatenate([[np.nan], adx]), periods)
    adx = pd.Series(adx)
    adx.index = df.index
    return adx

def qp(series:pd.Series, color:str = 'blue', lw:float=.5):
    '''Extremely quick function for plotting lines in a pleasant way without having to type plt constantly'''
    plt.plot(series.index, series, color=color, lw=lw)

def candle_plot(data:pd.DataFrame, divisor_1:int=1, divisor_2:int=1, title:str = None, show:bool = False):
    stock_prices = data
    up = stock_prices[stock_prices.close >= stock_prices.open] 
    down = stock_prices[stock_prices.close < stock_prices.open]
    
    col1 = 'green'
    col2 = 'red'
    lcol = 'black'
    
    # Setting width of candlestick elements 
    width = .5/(len(data))/divisor_1
    width2 = .05/(len(data))/divisor_2

    if show: plt.figure(figsize=(18, 6), dpi=100)
    
    # Plotting up prices of the stock 
    plt.bar(up.index, up.close-up.open, width, bottom=up.open, color=col1) 
    plt.bar(up.index, up.high-up.close, width2, bottom=up.close, color=lcol) 
    plt.bar(up.index, up.low-up.open, width2, bottom=up.open, color=lcol) 
    
    # Plotting down prices of the stock 
    plt.bar(down.index, down.close-down.open, width, bottom=down.open, color=col2) 
    plt.bar(down.index, down.high-down.open, width2, bottom=down.open, color=lcol) 
    plt.bar(down.index, down.low-down.close, width2, bottom=down.close, color=lcol) 
    
    # rotating the x-axis tick labels at 30degree  
    # towards right 

    plt.plot(stock_prices.index, stock_prices.open.ewm(span=2).mean(), lw=.5)
    plt.xticks(rotation=30, ha='right') 

    if title: plt.title(title)
    if show: plt.show()

def logo():
    return '''
┏┓┓         ┏┓  •   ┓┓
┣┫┃┏┓┏┓┏┏┓  ┗┓┏┓┓┏┓┏┫┃
┛┗┗┣┛┗┻┗┗┻  ┗┛┣┛┗┛┗┗┻┗
   ┛          ┛       '''