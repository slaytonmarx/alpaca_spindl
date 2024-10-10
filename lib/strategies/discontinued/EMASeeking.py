import sys
from lib.Portfolio import Portfolio; sys.path.append('../..')
from lib.Strategy import SelectionStrategy, Strategy
import lib.Toolbox as tb
import lib.TimeKeeper as tk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class EMASeeking(Strategy):
    '''Strategy where we use the squeeze momentum indicator and "powerful" short stop techniques.'''
    def __init__(self, symbol: str, port: Portfolio, context: SelectionStrategy, date: pd.DatetimeIndex = None,
                 archive_data:pd.DataFrame = None, tune:bool = False):
        super().__init__(symbol, port, context, date, archive_data, tune,
                         tuning_variables=[])
        
    def trade_command(self, index:pd.DatetimeIndex):
        '''Says to buy when our value is below our average and sell when above'''
        pindex = tb.get_previous_index(index, self.data)
        order = self.calculate_order(index)
        
        if self.failsafes(pindex): return True

        if self.has_stock():
            if self.sell_criteria(index, pindex): return self.add_market_transaction(index, 'sell', -1, 'NORM')
            elif self.shortbuy_criteria(index, pindex): return self.add_market_transaction(index, 'shortbuy', -1, 'NORM')
        elif not self.any_stock() and index.hour < tk.TRADE_END_HOUR:
            if self.buy_criteria(pindex): return self.add_market_transaction(index, 'buy', order, 'NORM')
            elif self.shortsell_criteria(pindex): return self.add_market_transaction(index, 'shortsell', order, 'NORM')

    def sell_criteria(self, pindex:pd.DatetimeIndex, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a sell order'''
        if not self.get_stock_sign(): return False
        order = self.port.get_last_order(self.symbol)
        #if index.hour == order.created_at.hour and index.minute == order.created_at.minute: return False
        profit = self.data.open.loc[index] - order.filled_avg_price

        span = self.data.close[order.created_at:pindex]
        ma = span.idxmax(); max_value = span.loc[ma]
        atr = self.atr.loc[ma] * self.conf.ATR_SELL
        if (self.data.open.loc[index] <= max_value - atr and profit > 0):# and self.avdel.loc[pindex] < 0:
            return True

    def shortbuy_criteria(self, pindex:pd.DatetimeIndex, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortbuy order'''
        if self.get_stock_sign(): return False
        order = self.port.get_last_order(self.symbol)
        #if index.hour == order.created_at.hour and index.minute == order.created_at.minute: return False
        profit = order.filled_avg_price - self.data.open.loc[index]

        span = self.data.close[order.created_at:pindex]
        mi = span.idxmin(); min_value = span.loc[mi]
        atr = self.atr.loc[mi] * self.conf.ATR_SELL
        if (self.data.open.loc[index] >= min_value + atr and profit > 0):# and self.avdel.loc[pindex] < 0:
            return True
    
    def buy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a buy order'''
        entry, dentry = self.emas.loc[index], self.demas.loc[index]
        pindex = tb.get_previous_index(index, self.data)
        if self.calculate_spread(entry): return False
        return ((entry.short > entry.mid > entry.long)
                and ((dentry.short > 0)
                     and (dentry.mid > 0)
                     and (dentry.long > 0))
                and (self.data.close.loc[pindex] < self.emas.short.loc[pindex]
                     and self.data.close.loc[index] > self.emas.short.loc[index])
                     )
    
    def shortsell_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortsell order'''
        entry, dentry = self.emas.loc[index], self.demas.loc[index]
        pindex = tb.get_previous_index(index, self.data)
        if self.calculate_spread(entry): return False
        return ((entry.short < entry.mid < entry.long)
                and ((dentry.short < 0)
                     and (dentry.mid < 0)
                     and (dentry.long < 0))
                and (self.data.close.loc[pindex] > self.emas.short.loc[pindex]
                     and self.data.close.loc[index] < self.emas.short.loc[index])
                     )

    def calculate_order(self, index:pd.DatetimeIndex):
        '''Returns an integer amount of stock to order when buying/short selling'''
        spending_cap = self.spending_cap
        order = int(spending_cap / self.data.open.loc[index] / self.conf.ORDER_DIVIDER / self.conf.ALLOCATION_DIVIDER) - 50
        if order < 0: order = 0
        return order

    def get_data(self, interval:str = '1m'):
        self.data = super().get_data(interval, start=self.date, buffer=1)
        self.atr = tb.get_atr(self.data)
        self.emas = pd.concat([self.data.close.ewm(span=150).mean(), self.data.close.ewm(span=100).mean(), self.data.close.ewm(span=50).mean()],axis=1)
        self.emas.columns = ['long','mid', 'short']
        self.demas = pd.concat([self.emas.short.diff().ewm(span=10).mean(), self.emas.mid.diff().ewm(span=10).mean(), self.emas.long.diff().ewm(span=10).mean()],axis=1)
        self.demas.columns = ['long','mid', 'short']
        return self.data

    def failsafes(self, index:pd.DatetimeIndex):
        # Shortstop Failsafe
        if self.has_stock():
            order = self.port.get_last_order(self.symbol)
            created, side = order.created_at, order.side
            
            atr = self.atr.loc[created] * self.conf.ATR_FACTOR
            if side == 'buy' and (self.data.open.loc[index] <= self.data.open.loc[created] - atr):
                return self.add_market_transaction(index, 'sell', -1, 'ATR Failsafe')
            elif side == 'sell' and (self.data.open.loc[index] >= self.data.open.loc[created] + atr):
                return self.add_market_transaction(index, 'shortbuy', -1, 'ATR Failsafe')
        return False
    
    def calculate_spread(self, entry:pd.DataFrame):
        closeness = abs(entry.short - entry.long) + abs(entry.mid - entry.long) + abs(entry.long - entry.mid)
        return closeness < .5
    
    def plot_line(self, msg:str = ''):
        '''Plots the graph'''
        #super().plot_line()
        plt.figure(dpi=200)
        plt.title(self.symbol + '\n'+ str(self.date)+' '+msg)
        plt.plot(self.data[self.date:].index, self.data.open[self.date:], lw=.5)
        
        plt.plot(self.emas[self.date:].index, self.emas[self.date:].long, color='red', lw=.5)
        plt.plot(self.emas[self.date:].index, self.emas[self.date:].mid, color='orange', lw=.5)
        plt.plot(self.emas[self.date:].index, self.emas[self.date:].short, color='green', lw=.5)

        if not self.symbol in self.port.orders: return
        for order in self.port.orders[self.symbol]:
            if order.mark == 1: plt.axvline(order.created_at, lw=.5, color='green')
            elif order.mark == 2: plt.axvline(order.created_at, lw=.5, color='orange')
            elif order.mark == -2: plt.axvline(order.created_at, lw=.5, color='blue')
            elif order.mark == -1: plt.axvline(order.created_at, lw=.5, color='red')
        plt.show()