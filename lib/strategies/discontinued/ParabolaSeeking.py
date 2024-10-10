import sys
from lib.Portfolio import Portfolio; sys.path.append('../..')
from lib.Strategy import Strategy
import lib.tools.Toolbox as tb
import lib.tools.TimeKeeper as tk
import lib.tools.Config as Config
import metadata.trade_configs.Globals as gb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import lib.tools.Logger as log

class ParabolaSeeking(Strategy):
    '''Strategy where we use the squeeze momentum indicator and "powerful" short stop techniques.'''
    def __init__(self, symbol: str, port: Portfolio, date: pd.DatetimeIndex = None, selector = None, conf:Config = None, sconf:Config = None):
        super().__init__(symbol, port, date, selector, conf, sconf)
        
    def trade_command(self, index:pd.DatetimeIndex):
        '''Says to buy when our value is below our average and sell when above'''
        self.ops_log(index)

        if self.failsafes(index): return None

        if self.has_stock():
            if self.sell_criteria(index): return self.add_transaction(index, 'sell', -1, 'NORM')
            elif self.shortbuy_criteria(index): return self.add_transaction(index, 'shortbuy', -1, 'NORM')
        elif not self.any_stock() and self.psar_flip.loc[index] and index.hour < gb.TRADE_END_HOUR:
            if self.buy_criteria(index): return self.add_transaction(index, 'buy', 1, 'NORM')
            elif self.shortsell_criteria(index): return self.add_transaction(index, 'shortsell', 1, 'NORM')

    def sell_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a sell order'''
        if not self.get_stock_sign(): return False
        order = self.port.get_last_order(self.symbol)
        profit = self.data.close.loc[index] - order.filled_avg_price
        #return self.data.loc[index].open > self.data.loc[index].close

        # PSAR FLIP
        if self.ha_flip.loc[index] and profit > 0: return True
        
    def shortbuy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortbuy order'''
        if self.get_stock_sign(): return False
        order = self.port.get_last_order(self.symbol)
        profit = order.filled_avg_price - self.data.close.loc[index]

        # PSAR FLIP
        if self.ha_flip.loc[index] and profit > 0: return True
    
    def buy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a buy order'''
        #tail = self.ha.loc[:index].iloc[:-1].tail(3)

        return (not self.psar_above.loc[index])# and ((tail.close-tail.open)<0).sum()==3: 
    
    def shortsell_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortsell order'''
        #tail = self.ha.loc[:index].iloc[:-1].tail(3)

        return (self.psar_above.loc[index]) # and ((tail.close-tail.open)>0).sum()==3:

    def get_data(self, update:bool = False):
        super().get_data(update)
        df = self.data.iloc[-40:] if update else self.data
        self.ha = tb.get_haiken_ashi(df)
        self.ha_flip = ((self.ha.open - self.ha.close) > 0).diff()
        self.psar = PSAR(self.datas[MID])
        self.psar_above = (df.close < self.psar)
        self.psar_flip = self.psar_above.diff()
        return self.data

    def failsafes(self, index:pd.DatetimeIndex):
        if self.has_stock():
            if (not hasattr(self, 'atr') or not self.atr):
                order = self.port.get_last_order(self.symbol)
                self.atr = tb.get_atr(self.data[order.created_at-pd.DateOffset(seconds=15*gb.PIP_DURATION):order.created_at]).iloc[-1]
        else: self.atr = None

        if self.has_stock():
            order = self.port.get_last_order(self.symbol)
            #profit = (self.data.open.loc[index] - order.filled_avg_price)*order.qty if side == 'buy' else (order.filled_avg_price - self.data.open.loc[index])*order.qty

            atr = self.atr * self.sconf.ATR_FACTOR
            #print(self.data.open.loc[index], self.atr * self.sconf.ATR_FACTOR)
            if order.side == 'buy' and self.data.open.loc[index] <= order.filled_avg_price - atr:
                return self.add_transaction(index, 'sell', -1, 'ATR Failsafe')
            elif order.side == 'sell' and self.data.open.loc[index] >= order.filled_avg_price + atr:
                return self.add_transaction(index, 'shortbuy', -1, 'ATR Failsafe')
        return None
    
    def ops_log(self, index:pd.DatetimeIndex):
        '''Logs information important to the squeeze'''
        log.log(self.port.api, index, self.symbol, 'OPS',
            {'close':round(self.data.close.loc[index],2),
                'psar_position':('UP' if self.data.close.loc[index] < self.psar.loc[index] else 'DOWN')
                })

    def plot_line(self, msg:str = ''):
        '''Plots the graph'''
        #super().plot_line()
        plt.figure(dpi=200)
        plt.title(self.symbol + '\n'+ str(self.date)+' '+msg)
        # plt.scatter(self.ha.iloc[-120:].index, self.ha.iloc[-120:].psar, s=.05)
        # tb.candle_plot(self.ha[self.date:].iloc[-120:])
        plt.scatter(self.data.index, self.psar, s=.05)
        # tb.candle_plot(self.ha[self.date:])
        #tb.candle_plot(self.data[self.date:], 10 ,10)
        tb.candle_plot(self.ha[self.date:], 10 ,10)
        
        if not self.symbol in self.port.orders: return
        for order in self.port.orders[self.symbol]:
            #print(order.created_at)
            #if order.created_at < self.data.index[-120]: continue
            if order.mark == 1: plt.axvline(order.created_at, lw=.15, color='green')
            elif order.mark == 2: plt.axvline(order.created_at, lw=.15, color='orange')
            elif order.mark == -2: plt.axvline(order.created_at, lw=.15, color='blue')
            elif order.mark == -1: plt.axvline(order.created_at, lw=.15, color='red')
        
        plt.show()