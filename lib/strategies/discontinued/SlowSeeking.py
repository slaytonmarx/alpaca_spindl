import sys
from lib.Portfolio import Portfolio; sys.path.append('../..')
from lib.Strategy import Strategy
from lib.indicators.RSI import RSI
from lib.indicators.SqueezeMomentum import SqueezeMomentum
from lib.indicators.ForebodingWick import ForebodingWick
import metadata.trade_configs.Globals as gb
import lib.tools.Toolbox as tb
import lib.tools.TimeKeeper as tk
import lib.tools.Config as Config
import pandas as pd
import matplotlib.pyplot as plt
import lib.tools.Logger as log

class SlowSeeking(Strategy):
    '''Strategy where we listen to a number of different technical indicators to make our decisions.'''
    def __init__(self, symbol: str, port: Portfolio, date: pd.DatetimeIndex = None, conf:Config = None, sconf:Config = None):
        '''Populates the data using get data.'''
        super().__init__(symbol, port, date, conf, sconf)
        self.spending_cap = self.port.cash / self.conf.ALLOCATION_DIVIDER
        
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
            # self.rsi.get_signal(index) == -1
            (self.data.close.loc[index] > self.port.get_price(self.symbol) + atr)
            and self.get_profit(index, 'sell') > 0): return True

    def shortbuy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortbuy order'''
        if self.get_stock_sign(): return False
        atr = self.atr * self.sconf.ATR_SELL
        if (
            # self.rsi.get_signal(index) == 1
            (self.data.close.loc[index] < self.port.get_price(self.symbol) - atr)
            and self.get_profit(index, 'buy') > 0): return True
    
    def buy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a buy order'''
        if (
            self.rsi.get_signal(index) == 1
            #and self.wicks.get_signal(index) == 1
            and self.squeeze.get_signal(index) == 1
        ): return True
    
    def shortsell_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortsell order'''
        if (
            self.rsi.get_signal(index) == -1
            #and self.wicks.get_signal(index) == -1
            and self.squeeze.get_signal(index) == -1
        ): return True

    def get_data(self, update:bool = False):
        super().get_data(update)
        if not update:
            self.rsi = RSI(self.data, self.sconf.RSI_WINDOW, self.sconf.RSI_STRICTNESS)
            self.squeeze = SqueezeMomentum(self.data, self.sconf.KC_WINDOW, self.sconf.BOL_DEV, self.sconf.SQUEEZE_DURATION)
            # self.wicks = ForebodingWick(self.data)
        else:
            self.rsi.update(self.data)
            self.squeeze.update(self.data)
            # self.wicks.update(self.data)
        return self.data

    def failsafes(self, index:pd.DatetimeIndex):
        if self.has_stock():
            if (not hasattr(self, 'atr') or not self.atr):
                order = self.port.get_last_order(self.symbol)
                i = tb.get_i(order.created_at, self.data)
                self.atr = tb.get_atr(self.data.iloc[i-15:i]).iloc[-1]
        else: self.atr = None

        if self.has_stock():
            order = self.port.get_last_order(self.symbol)
            #profit = (self.data.open.loc[index] - order.filled_avg_price)*order.qty if side == 'buy' else (order.filled_avg_price - self.data.open.loc[index])*order.qty

            atr = self.atr * self.sconf.ATR_FACTOR
            #print(self.data.open.loc[index], self.atr * self.sconf.ATR_FACTOR)
            if order.side == 'buy' and self.data.open.loc[index] <= order.filled_avg_price - atr: return self.add_transaction(index, 'sell', -1, 'ATR Failsafe')
            elif order.side == 'sell' and self.data.open.loc[index] >= order.filled_avg_price + atr: return self.add_transaction(index, 'shortbuy', -1, 'ATR Failsafe')

        day_change = self.port.get_day_change()
        if self.conf.WALKAWAY and not self.has_stock() and day_change >= self.conf.WALKAWAY_PROFIT:
            return True

        return False

    def ops_log(self, index:pd.DatetimeIndex):
        '''Logs information important to the squeeze'''
        # log.log(self.api, index.round(str(gb.PIP_DURATION)+'s'), self.symbol, 'OPS',
        #     {'close':round(self.data.close.loc[index],2),
        #         'volume':self.data.volume.loc[index]})

    def plot_line(self, msg:str = ''):
        '''Plots the graph'''
        #super().plot_line()
        plt.figure(figsize=(18, 6), dpi=100)
        tb.candle_plot(self.data[self.date:],title=self.symbol + '\n'+ str(self.date)+' '+msg)

        if not self.symbol in self.port.orders: return
        for order in self.port.orders[self.symbol]:
            if order.mark == 1: plt.axvline(order.created_at, lw=.5, color='green')
            elif order.mark == 2: plt.axvline(order.created_at, lw=.5, color='orange')
            elif order.mark == -2: plt.axvline(order.created_at, lw=.5, color='blue')
            elif order.mark == -1: plt.axvline(order.created_at, lw=.5, color='red')
        plt.show()