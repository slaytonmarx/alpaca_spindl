from lib.Selector import Selector
from lib.Strategy import Strategy
from lib.Portfolio import Portfolio
from lib.strategies.MomentumSeeking import MomentumSeeking
from lib.selectors.SimpleSelection import SimpleSelection
from tqdm import tqdm
import lib.tools.TimeKeeper as tk
import lib.tools.Scrivener as sc
import lib.tools.Toolbox as tb
import os.path as pa
from lib.tools.Config import Config
import traceback
import pandas as pd

class RoboTrader:
    ''' Scans the stock market for stocks to enter positions. Exits positions to harvest money.
    '''
    def __init__(self, api = None, config:Config = Config('base.json'), selector:Selector = SimpleSelection, strategy:Strategy = MomentumSeeking, symbols:list = []):
        self.api, self.port, self.config, self.selector, self.strategy, self.forced_stocks, self.run_date = api, Portfolio(api), config, selector, strategy, symbols, tk.today()

    def trade_cycle(self):
        '''The actual cycle of keeping a vigilent eye on the market and seeing if we should trade'''
        print(tb.logo())
        if tk.is_after(time=tk.get_trade_open()): self.bullcall()
        while True:
            if tk.keep_time(self.port, sc): self.bullcall()
            print(tk.now())
            # self.trade(tk.now())
            try: self.trade(tk.now())
            except Exception as e:
               sc.post_to_slack('Error\n'+str(traceback.format_exc()))
               print(traceback.format_exc())
            tk.sync(self.port.api)
            if tk.is_time(10,00) or tk.is_time(12,00) or tk.is_time(14,00): sc.post_to_slack(str(self.port))
        
    def trade(self, index:pd.DatetimeIndex):
        '''The most fundamental function in our RoboTrader, tells the RoboTrader whether to buy or sell the good, and by how much.'''
        for ticker in self.strategies.values():
            if self.api:
                ticker.get_data(update=True)
                index = ticker.data.index[-1]
            if tk.is_before(15, 50,index):
                trade = ticker.trade_command(index)
                if trade and self.api:
                    print(trade)
                    #message = trade.symbol+' ['+trade.side+'] '+str(trade.qty)
                    #sc.post_to_slack(message)
            elif self.config.CASHOUT and tk.is_after(15, 50, index):
                ticker.cashout(index)
            
            if not self.api and ticker.data.index[-1] == index: ticker.cashout(index)

    def bullcall(self, date = None, sconfs = []):
        '''Consults with the animal spirits to find the bulls from the bears on a particular day, populating our
            symbols dictionary, i.e, uses Ticker to determine whether our price will increase for the day for
            each symbol.
        '''
        date = tk.today() if not date else date
        self.bulls, selectors = [], {}
        if not self.forced_stocks:
            self.forced_stocks = sc.load_symbols()
            bulls_to_bank_on = self.config.BULLS_TO_BANK_ON
        else: bulls_to_bank_on = len(self.forced_stocks)

        bulls_scored = []
        if self.selector == SimpleSelection:
            for symbol in self.forced_stocks:
                selector = self.selector(symbol, date, self.strategy)
                selector_score = selector.is_valid()
                if not selector_score: continue
                bulls_scored.append({'score':selector_score,'symbol':symbol})
                selectors[symbol] = selector
        else:
            for symbol in tqdm(self.forced_stocks, desc='Performing Analysis on Symbols'):
                selector = self.selector(symbol, date, self.strategy)
                selector_score = selector.is_valid()
                if not selector_score: continue
                bulls_scored.append({'score':selector_score,'symbol':symbol})
                selectors[symbol] = selector
        try:
            for symbol in pd.DataFrame(bulls_scored).sort_values('score').iloc[-bulls_to_bank_on:].symbol:
                self.bulls.append(symbol)
        except KeyError:
            raise self.NoProfitableSymbolsException
        
        self.config.BULL_COUNT = len(self.bulls)
        self.strategies = {symbol: self.strategy(symbol, self.port, date, selectors[symbol], self.config,  sconfs[symbol] if symbol in sconfs else None) for symbol in self.bulls}
        if self.api: print('OUR BULLS TODAY ARE:',list(self.bulls)); tk.wait((1000000-self.api.get_clock().timestamp.microsecond)/1000000)
    
    def trade_simulation(self, date:pd.DatetimeIndex, sconfs:dict = [], starting_capital:float = None):
        '''Runs an experiment for the given strategy, attempting to trade at each minute of the given day'''
        self.bullcall(date, sconfs)
        self.port.day_start_cash = self.port.cash if not starting_capital else starting_capital
        if len(self.strategies) == 0: return self.strategies
        for index in list(self.strategies.values())[0].data.index[:-1]:
            if index < tk.get_trade_open(date): continue
            self.trade(index)
        for ticker in self.strategies.values(): ticker.cashout(index)
        return self.strategies
    
    class NoProfitableSymbolsException(Exception):
        pass