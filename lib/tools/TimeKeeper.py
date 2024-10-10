import metadata.trade_configs.Globals as gb
import alpaca_trade_api as alp
import datetime
import time
import pandas as pd
import pytz

def get_market_open(date:pd.DatetimeIndex = datetime.datetime.now(pytz.timezone('America/New_York'))):
    '''Returns the date value of the day's market open'''
    return date.replace(hour=9,minute=30,second=0,microsecond=0)

def get_trade_open(date:pd.DatetimeIndex = datetime.datetime.now(pytz.timezone('America/New_York'))):
    '''Returns the date value of the day's market open'''
    return date.replace(hour=gb.TRADE_START_HOUR,minute=gb.TRADE_START_MINUTE,second=0,microsecond=0)

def get_midday(date:pd.DatetimeIndex = datetime.datetime.now(pytz.timezone('America/New_York'))):
    '''Returns the date value of the day's market open'''
    return date.replace(hour=12,minute=0,second=0,microsecond=0)

def get_market_close(date:pd.DatetimeIndex = datetime.datetime.now(pytz.timezone('America/New_York'))):
    '''Returns the date value of the day's market close'''
    date = date.replace(hour=16,minute=0,second=0,microsecond=0)
    return pd.to_datetime(date)

def get_cease_buy(date:pd.DatetimeIndex = datetime.datetime.now(pytz.timezone('America/New_York'))):
    '''Returns when we are set to stop attempting to buy things based on globals'''
    return pd.to_datetime(date.replace(hour=gb.TRADE_END_HOUR,minute=0,second=0, microsecond=0))

def is_after(hour:int=0, minute:int=0, now=datetime.datetime.now(pytz.timezone('America/New_York')), time=None):
    '''Way of checking that the time is after a certain point'''
    if time: return now > time
    return int(now.hour) > hour or (int(now.hour) == hour and int(now.minute) >= minute)

def is_before(hour:int, minute:int, time=None):
    '''Way of checking that the time is after a certain point'''

    if time == None: time = datetime.datetime.now(pytz.timezone('America/New_York'))
    if int(time.hour) < hour: 
        return True
    elif int(time.hour) == hour:
        if int(time.minute) < minute:
            return True
    return False

def is_time(hour:int, minute:int, time=None):
    '''Way of checking that the time is a certain point'''

    if time == None: time = datetime.datetime.now(pytz.timezone('America/New_York'))
    if int(time.hour) == hour and int(time.minute) == minute and int(time.second) == 0: return True
    return False

def hold(message:str, delta, now, scrivener):
    '''Waits for a certain amount of time'''
    ds = int(delta.seconds) + 1
    msg = message_heading('Waiting until market opening in '+str(round(delta.total_seconds()/60/60,2))+' hours\n'+message, now)
    scrivener.post_to_slack(msg)
    time.sleep(ds)
    now = datetime.datetime.now(pytz.timezone('America/New_York'))
    wakeup_message = message_heading("Ok ok, getting back to work!", now)
    scrivener.post_to_slack(wakeup_message)

def message_heading(msg:str, now:pd.DatetimeIndex):
    top_line = '====================='+now.today().strftime('%a %b,%d,%Y')+'======================'
    msg = (top_line+'\n'+
            msg+'\n'+
            '='*len(top_line)+'\n')
    return msg


def keep_time(port, scrivener):
    '''Holds depending on weather or not the market is actually open. If we return true that means we've slept through the night
        and need to reasses the porfolio and redo some things.
    '''
    now = datetime.datetime.now(pytz.timezone('America/New_York'))

    # check if weekend
    if now.today().weekday() > 4:
        days_till_monday = 7-now.today().weekday()
        hold('"Asking me to clock in on the weekend, the nerve" zzz...', (get_trade_open() + datetime.timedelta(days=days_till_monday)) - now, now, scrivener)
        return True

    # check if beforehours
    if now < get_trade_open(now):
        hold('"Hey, gimme five more minutes, I can sleep a little longer" zzz...', get_trade_open() - now, now, scrivener)
        return True

    # check if afterhours
    if now > get_market_close(now):
        hold('"Call back tomorrow, I am OFF THE CLOCK" zzz...', (get_trade_open() + datetime.timedelta(days=1)) - now, now, scrivener)
        return True
    
    # check if not buying and have nothing to sell
    if now > get_cease_buy(now) and not port.has_stock():
        hold('"Oh, whelp, it looks like we are GOOOOOD for trading, guess I get to go to bed early today"', (get_trade_open() + datetime.timedelta(days=1)) - now, now, scrivener)
        return True

    return False

def get_midnight(date:pd.DatetimeIndex = None):
    '''Returns the 00:00:00 datetime index for a given date. Returns midnight of today if no date is specified'''
    if not date: date = pd.to_datetime(datetime.datetime.now(tz=pytz.timezone('America/New_York')).replace(hour=0, minute=0 ,second=0, microsecond=0))
    return (date - pd.DateOffset(hours=date.hour, minutes=date.minute, seconds=date.second, microseconds=date.microsecond)).round('s')

def get_workday(data:pd.DataFrame, date:pd.DatetimeIndex = None):
    '''Returns only the period of time of the given day in which the market was open, i.e, 9:30am to 4:00pm. Returns
        today's workday if no date is specified.
    '''
    if not date: date = pd.to_datetime(datetime.datetime.now(tz=pytz.timezone('America/New_York')))
    #return data[f'{date.year}-{date.month}-{date.day} 09:30:00-04:00':f'{date.year}-{date.month}-{date.day} 16:00:00-04:00']
    return data[get_market_open(date):get_market_close(date)]

def get_ideal_workday(date:datetime.datetime):
    '''Returns a pandas series with minute by minute timestamps.'''
    r = pd.Series(pd.date_range(get_trade_open(date), periods=400, freq="1min"))
    lim = pd.Index(r).get_loc(get_market_close(date))
    return r[:lim]

def get_date_range(start:pd.DatetimeIndex, periods:int, frequency:str):
    return pd.Series(pd.date_range(start, periods=periods, freq=frequency))

def d(month:int, day:int, hour:int=0, minute:int=0, second:int=0, year:int=None):
    '''Returns the inputted time as a string acceptable by our dataframes'''
    if not year: year = datetime.datetime.now().year
    month, day, hour, minute, second = str(month).rjust(2, '0'), str(day).rjust(2, '0'), str(hour).rjust(2, '0'), str(minute).rjust(2, '0'), str(second).rjust(2, '0')
    return pd.to_datetime(f'{year}-{month}-{day} {hour}:{minute}:{second}').tz_localize(pytz.timezone('America/New_York'))

def to_time_s(month:int, day:int, hour:int=0, minute:int=0, year:int=None):
    '''Returns the inputted time as a string acceptable by our dataframes'''
    if not year: year = datetime.datetime.now().year
    month, day, hour, minute = str(month).rjust(2, '0'), str(day).rjust(2, '0'), str(hour).rjust(2, '0'), str(minute).rjust(2, '0')

    return f'{year}-{month}-{day}T{hour}:{minute}:00-04:00'

def dto_time(date:pd.DatetimeIndex):
    '''Returns the date index as a string'''
    year, month, day, hour, minute, second = date.year, str(date.month).rjust(2, '0'), str(date.day).rjust(2, '0'), str(date.hour).rjust(2, '0'), str(date.minute).rjust(2, '0'), str(date.second).rjust(2, '0')

    return f'{year}-{month}-{day}T{hour}:{minute}:{second}-04:00'

def tsto_time(timestamp:int):
    '''Converts the bar timestamps to datetime indexes'''
    return pd.to_datetime(timestamp).tz_localize(pytz.UTC).tz_convert(pytz.timezone('America/New_York'))

def tunit(string:str):
    '''Returns timeframe unit used by alpaca'''
    match string:
        case 'm': return alp.TimeFrame.Minute
        case '5m': return alp.TimeFrame(5, alp.TimeFrameUnit('Min'))
        case '15m': return alp.TimeFrame(15, alp.TimeFrameUnit('Min'))
        case '30m': return alp.TimeFrame(30, alp.TimeFrameUnit('Min'))
        case 'h': return alp.TimeFrame.Hour
        case 'd': return alp.TimeFrame.Day
    
def get_up_to(data:pd.DataFrame, hour:int, minute:int):
    '''Returns a subset of the data up to the hour and minute given'''
    return data[:d(data.index[0].month, data.index[0].day, hour, minute)]

def get_yesterday(data:pd.DataFrame, date:pd.DatetimeIndex):
    '''Returns whatever index immediately proceeded this one'''
    return data.index[data.index.get_loc(date)-1]

def now(): return pd.to_datetime(datetime.datetime.now(tz=pytz.timezone('America/New_York'))).round('s')
def rnow(): return pd.to_datetime(datetime.datetime.now(tz=pytz.timezone('America/New_York')))

def today(): return get_midnight()

def get_date_range(start:pd.DatetimeIndex = None, end:pd.DatetimeIndex = None, lookback:int = 0):
    '''Gives a date range of the business days either between two days or looking back from today backwards by a value of lookback'''
    if start and end: return pd.date_range(start=start, end=end, freq='B')
    elif start and lookback: return pd.date_range(start=start-pd.DateOffset(days=abs(lookback)), end=start, freq='B')
    elif lookback: return pd.date_range(start=today()-pd.DateOffset(days=abs(lookback)), end=today(), freq='B')
    else: pd.date_range(start=today()-pd.DateOffset(days=abs(1)), end=today(), freq='B')

def give_n_days_ago(date:pd.DatetimeIndex, lookback_initial:int):
    '''Returns a set of business days of lookback_initial length from the given day'''
    lookback = lookback_initial
    while len(get_date_range(date - pd.DateOffset(days=lookback+1), date - pd.DateOffset(days=1))) < lookback_initial: lookback += 1
    return lookback

def in_tick(index:pd.DatetimeIndex):
    return now() < index + pd.DateOffset(seconds=int(60*3))

def sync(api):
    '''Syncs up our trade actions to the present moment of stocks'''
    #sleep_time = (TICK_DURATION - now().second % TICK_DURATION)# if not port.has_stock() else (SHORT_TICK_DURATION - now().second % SHORT_TICK_DURATION)
    sleep_time = (60 - api.get_clock().timestamp.second % 60) + gb.PIP_OFFSET
    print('sleeping for', sleep_time)
    time.sleep(sleep_time)

    t = api.get_clock().timestamp.second
    while t < gb.PIP_OFFSET:
        print('\tNOT QUITE THERE', t)
        wait(0.001)
        t = api.get_clock().timestamp.second
    wait(0.001)

def wait(seconds:float, show:bool = False):
    if show: print('waiting', seconds)
    time.sleep(seconds)