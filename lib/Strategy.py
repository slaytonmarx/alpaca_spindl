import sys; sys.path.append('../../..'); sys.path.append('../..')
from lib.Portfolio import Portfolio
from lib.tools.Config import Config
from lib.tools.Gambit import Gambit
from lib.Selector import Selector
import metadata.trade_configs.Globals as gb
import lib.tools.Broker as br
import lib.tools.Toolbox as tb
import lib.tools.Scrivener as sc
import lib.tools.TimeKeeper as tk
import lib.tools.Logger as log
import matplotlib.pyplot as plt
import pandas as pd

class Strategy:
    '''Class for determine whether to buy or sell at a given timestamp, and how much to buy or sell.'''
    def __init__(self, symbol:str, port:Portfolio = None, date:pd.DatetimeIndex = None, selector:Selector = None, conf:Config = None, sconf:Config = None, pips:list = []):
        '''Sets up the portfolio, date, and conf, and runs the initial get data'''
        if selector:
            if hasattr(selector, 'sconf'): sconf = selector.sconf
        if not port: port = Portfolio(None)
        if not conf: conf = Config()
        if not sconf: sconf = Config('s_'+self.__class__.__name__+'_'+symbol+'.json')
        if not len(sconf.jdict): sconf = Config('s__default')
        if not hasattr(conf, 'BULL_COUNT'): conf.BULL_COUNT = 1

        self.symbol, self.port, self.api, self.conf, self.sconf, self.pips, self.least_value = symbol, port, port.api, conf, sconf, pips if len(pips) > 0 else [[gb.PIP_DURATION,1]], 0
        self.spending_cap, self.ticker_profit = self.port.cash / self.conf.BULL_COUNT / self.conf.ALLOCATION_DIVIDER, 0
        self.date = date if date else tk.today()
        self.get_data()

    def trade_command(self, index:pd.DatetimeIndex):
        '''The most essential command for any Stock. Determines when to buy the stock and how
            much to buy when doing so.
        '''
        if self.failsafes(): return

        if self.get_trade_type(index):
            if self.sell_criteria(index): self.add_transaction(self.symbol, self.port, self, -5, index)
            elif self.buy_criteria(index): self.add_transaction(self.symbol, self.port, self, 1, index)
        else:
            if self.shortbuy_criteria(index): self.add_transaction(self.symbol, self.port, self, 1, index)
            elif self.shortsell_criteria(index): self.add_transaction(self.symbol, self.port, self, -5, index)

    def update_values(self, index:pd.DatetimeIndex):
        '''Updates all values that will be used by the trade_command to the current index.'''
        self.value = self.data.open.loc[index]

    def sell_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a sell order'''
        return False

    def shortbuy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortbuy order'''
        return False
    
    def buy_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a buy order'''
        return False

    def shortsell_criteria(self, index:pd.DatetimeIndex):
        '''Returns True if the correct criteria have been met to place a shortsell order'''
        return False

    def failsafes(self, index:pd.DatetimeIndex):
        '''Contains a suite of failsafes to prevent losses and ensure profits'''

    def get_data(self, update:bool = False):
        '''Pulls the given day's data. If update then we only pull a single minute and update our existing data'''
        if update and hasattr(self, 'data') and tk.in_tick(self.data.index[-1]):
            bar = sc.get_bar(self.symbol, api=self.port.data_api)
            self.data = sc.easy_concat(self.data, bar)
        else:
            self.datas = sc.update_archive(self.symbol, self.date, self.pips, api=self.port.data_api) if gb.ALLOW_UPDATE else sc.get_archives(self.symbol, self.date, self.pips, api=self.port.data_api)
            self.data = list(self.datas.values())[0]

    def get_profit(self, index:pd.DatetimeIndex, side:str):
        order = self.port.get_last_order(self.symbol)
        going_rate = self.data.loc[index].close
        if 'sell' in side: return going_rate - order.filled_avg_price
        elif 'buy' in side: return order.filled_avg_price - going_rate
    
    def calculate_order(self, price:float, qty_code:int):
        if qty_code == 1:
            quantity = int(self.spending_cap / price / self.conf.ORDER_DIVIDER) - 5
            if self.api: print('OUR ORDER IS ',quantity,'DUE TO',self.spending_cap, price, self.conf.ORDER_DIVIDER)
            if quantity < 0: quantity = 0
        elif qty_code == -1:
            quantity = self.port.get_qty(self.symbol) if self.symbol in self.port.positions else 0
        elif qty_code == -2:
            quantity = int(self.port.get_qty(self.symbol)/2) if self.symbol in self.port.positions else 0
        return quantity

    def add_transaction(self, index:pd.DatetimeIndex, trade_code:str, qty_code:int, msg:str = '', failsafe:bool = False):
        '''If we are currently trading, creates a gambit of the desired type, otherwise simply executes a historical trade'''
        # CALCULATE PRICE
        if self.api: price = self.port.calculate_live_price(self.symbol); print('OUR PRICE IS', price)
        else:
            next_i = tb.get_i(index, self.data)+1
            match trade_code:
                 # "Broker Accurate" Settings
                # case 'buy': price = self.port.calculate_live_price(self.symbol, index) + gb.PRICE_BUFFER
                # case 'shortsell': price = self.port.calculate_live_price(self.symbol, index) - gb.PRICE_BUFFER
                # case 'sell': price = self.port.calculate_live_price(self.symbol, index) - gb.PRICE_BUFFER
                # case 'shortbuy': price = self.port.calculate_live_price(self.symbol, index) + gb.PRICE_BUFFER

                # Avoid Potholes/Speedbumps
                case 'buy': price = self.data.open.iloc[next_i] + gb.PRICE_BUFFER
                case 'shortsell': price = self.data.open.iloc[next_i] - gb.PRICE_BUFFER
                case 'sell': price = self.data.open.iloc[next_i] - gb.PRICE_BUFFER
                case 'shortbuy': price = self.data.open.iloc[next_i] + gb.PRICE_BUFFER

                # "FEEL GOOD" Settings
                # case 'buy': price = self.data.low.iloc[next_i] + gb.PRICE_BUFFER
                # case 'shortsell': price = self.data.high.iloc[next_i] - gb.PRICE_BUFFER
                # case 'sell': price = (self.data.high.iloc[next_i]) - gb.PRICE_BUFFER
                # case 'shortbuy': price = (self.data.low.iloc[next_i]) + gb.PRICE_BUFFER
            # if (trade_code == 'buy' and price < self.data.low.iloc[next_i]) or (trade_code == 'shortsell' and price > self.data.high.iloc[next_i]):
            #     #print('FAILED TO ENTER WITH', trade_code, 'AT', index)
            #     # print(price, self.data.low.iloc[next_i], price < self.data.low.iloc[next_i])
            #     return
            # if (trade_code == 'sell' and price > self.data.high.iloc[next_i]) or (trade_code == 'shortbuy' and price < self.data.low.iloc[next_i]):
            #     #print('FAILED TO ENTER WITH', trade_code, 'AT', index)
            #     # print(price, self.data.low.iloc[next_i], price < self.data.low.iloc[next_i])
            #     return
            
        # CALCULATE ORDER FROM PRICE
        quantity = self.calculate_order(price, qty_code)
        if quantity == 0: return None

        # PERFORM TRANSACTION
        if self.api:
            print('ATTEMPTING TO', trade_code, 'FOR AN AMOUNT OF', quantity)
            gambit = Gambit(self.port, self.symbol, price, quantity, trade_code, msg, failsafe)
            order = gambit.order
        else:
            if trade_code == 'buy' or trade_code == 'shortsell': profit = 0
            else: profit = (self.get_profit(index, 'sell'))*quantity if trade_code == 'sell' else (self.get_profit(index, 'buy'))*abs(quantity)
            order = self.port.historic_order(self, index, trade_code, quantity, price)
            order_log = {'type':'limit','side':trade_code.upper(), 'filled_price':order.filled_avg_price, 'qty':order.qty, 'profit':profit, 'note':msg}
            self.ticker_profit += profit
            if hasattr(self, 'atr'): order_log['atr'] = self.atr
            log.log(self.port.api, index, self.symbol, 'ORDERS', order_log)
        return order

    def ops_log(self, index:pd.DatetimeIndex):
        '''Defines the basic information that the given strategy will log at each index'''

    def has_stock(self):
        '''Returns whether we have a given stock'''
        return self.port.has_stock(self.symbol)
    
    def any_stock(self):
        '''Returns whether we have any open positions at all'''
        return self.port.has_stock()

    def get_stock_sign(self):
        '''Returns whether we are holding a short, or normal stock. Returns True for positive and False for negative'''
        return self.port.get_stock_sign(self.symbol)

    def cashout(self, index:pd.DatetimeIndex):
        '''Cashes out the remaining stock in our portfolio (Note, can lead to significant losses)
            if called at a poor time, does not check for loss so long as we don't go past the point
            of no return.
        '''
        if not self.has_stock(): return
        if self.api: print('CASHING OUT',self.symbol,'NOW')
        if self.get_stock_sign(): self.add_transaction(index, 'sell', -1, 'CASHOUT')
        else: self.add_transaction(index, 'shortbuy', -1, 'CASHOUT')

    def plot_line(self):
        '''Plots the line of the strategy'''
        plt.figure(dpi=150)
        plt.plot(self.data[self.date:].index, self.data[self.date:].open, lw=.75)
        plt.title(self.symbol + '   ' + str(self.date))
