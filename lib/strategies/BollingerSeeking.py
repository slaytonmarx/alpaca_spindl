import sys
from lib.Portfolio import Portfolio; sys.path.append('../..')
from lib.Strategy import Strategy
import metadata.trade_configs.Globals as gb
import lib.tools.Toolbox as tb
import lib.tools.TimeKeeper as tk
import lib.tools.Config as Config
import pandas as pd
import matplotlib.pyplot as plt
import lib.tools.Logger as log

class BollingerSeeking(Strategy):
    '''Strategy uses two bollinger band calculations, one derived from minute highs and one derived from minute lows, and uses them in a similar way to normal bollinger based strategy,
        i.e, when we cross from above the highband, we shortsell and when we cross from below the lowband, we buy. Uses initial value + ATR to determine when to clear the stock.
    '''
    def __init__(self, symbol: str, port: Portfolio, date: pd.DatetimeIndex = None, selector = None, conf:Config = None, sconf:Config = None):
        '''Populates the data using get data.'''
        super().__init__(symbol, port, date, selector, conf, sconf, pips=[[gb.PIP_DURATION,1]])
        
    def trade_command(self, index:pd.DatetimeIndex):
        '''Says to buy when our value is below our average and sell when above'''
        self.ops_log(index)
        
        if self.failsafes(index): return None

        if self.has_stock():
            if self.sell_criteria(index): return self.add_transaction(index, 'sell', -1, 'NORM')
            elif self.shortbuy_criteria(index): return self.add_transaction(index, 'shortbuy', -1, 'NORM')
        elif index.hour < gb.TRADE_END_HOUR:
            if self.buy_criteria(index): return self.add_transaction(index, 'buy', 1, 'NORM')
            elif self.shortsell_criteria(index): return self.add_transaction(index, 'shortsell', 1, 'NORM')

    def sell_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a sell order'''
        if not self.get_stock_sign(): return False
        atr = self.atr * self.sconf.ATR_SELL

        if (
            (self.data.close.loc[index] < self.port.get_price(self.symbol) + atr)
             ): return True
        return False

    def shortbuy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortbuy order'''
        if self.get_stock_sign(): return False
        atr = self.atr * self.sconf.ATR_SELL

        if (
            (self.data.close.loc[index] < self.port.get_price(self.symbol) - atr)
            ): return True
        return False
    
    def buy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a buy order'''
        i = tb.get_i(index, self.data)
        if (
            self.hbol.lowband.iloc[i] > self.lbol.highband.iloc[i]
            and self.hbol.lowband.iloc[i-1] < self.lbol.highband.iloc[i-1]
            ):
            return True
    
    def shortsell_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortsell order'''
        i = tb.get_i(index, self.data)
        if (
            self.hbol.lowband.iloc[i] < self.lbol.highband.iloc[i]
            and self.hbol.lowband.iloc[i-1] > self.lbol.highband.iloc[i-1]
        ):
            return True

    def get_data(self, update:bool = False):
        super().get_data(update)
        if not update:
            self.hbol = tb.get_bollinger_bands(self.data.high.ewm(span=self.sconf.BOL_EWM).mean(), num_stds=(self.sconf.BOL_DEV,0,-self.sconf.BOL_DEV))
            self.lbol = tb.get_bollinger_bands(self.data.low.ewm(span=self.sconf.BOL_EWM).mean(), num_stds=(self.sconf.BOL_DEV,0,-self.sconf.BOL_DEV))
        return self.data

    def failsafes(self, index:pd.DatetimeIndex):
        if self.has_stock():
            if (not hasattr(self, 'atr') or not self.atr):
                order = self.port.get_last_order(self.symbol)
                i = tb.get_i(order.created_at, self.data)
                self.atr = tb.get_atr(self.data.iloc[i-15:i]).iloc[-1]
        else: self.atr = None

        # Clear after exceeding ATR by ATR_FACTOR
        if self.has_stock():
            order = self.port.get_last_order(self.symbol)
            atr = self.atr * self.sconf.ATR_FACTOR
            if order.side == 'buy' and self.data.close.loc[index] <= order.filled_avg_price - atr: return self.add_transaction(index, 'sell', -1, 'ATR Failsafe')
            elif order.side == 'sell' and self.data.close.loc[index] >= order.filled_avg_price + atr: return self.add_transaction(index, 'shortbuy', -1, 'ATR Failsafe')

        return None
    
    def ops_log(self, index:pd.DatetimeIndex):
        '''Logs information important to the squeeze'''
        log.log(self.api, index.round(str(60)+'s'), self.symbol, 'OPS',
            {'close':round(self.data.close.loc[index],2),
             'bollinger_high':round(self.hbol.highband.loc[index],2),
                'volume':self.data.volume.loc[index]})

    def plot_line(self, msg:str = ''):
        '''Plots the graph'''
        #super().plot_line()
        plt.figure(figsize=(18, 6), dpi=100)
        tb.candle_plot(self.data[self.date:],title=self.symbol + '\n'+ str(self.date)+' '+msg)

        #plt.scatter(self.minima.index, self.minima.values, c='blue')
        #plt.scatter(self.maxima.index, self.maxima.values, c='orange')
        tb.qp(self.hbol.lowband[self.date:], color='green')
        tb.qp(self.lbol.highband[self.date:], color='red')

        if not self.symbol in self.port.orders: return
        for order in self.port.orders[self.symbol]:
            if order.mark == 1: plt.axvline(order.created_at, lw=.5, color='green')
            elif order.mark == 2: plt.axvline(order.created_at, lw=.5, color='orange')
            elif order.mark == -2: plt.axvline(order.created_at, lw=.5, color='blue')
            elif order.mark == -1: plt.axvline(order.created_at, lw=.5, color='red')
        plt.show()