from lib.RoboTrader import RoboTrader
from lib.Selector import Selector
from lib.strategies.BollingerSeeking import BollingerSeeking
import lib.tools.Scrivener as sc
import pandas as pd

class TuningSelection(Selector):
    '''Simulates the last day of trading. If yesterday we would have lost money we abstain today'''
    def __init__(self, name:str, date:pd.Timestamp):
        super().__init__(name, date)
    
    def is_valid(self):
        dates = pd.date_range(start=self.date-pd.DateOffset(days=4), end=self.date-pd.DateOffset(days=1), freq='B')
        results, final_total = [], 0
        for date in dates:
            trader = RoboTrader(None, strategy=BollingerSeeking, symbols=[self.symbol])
            try: tickers = trader.trade_simulation(date)
            except: print('skipping',date); continue
            tickers = trader.trade_simulation(date)
            day_profit = trader.port.cash-100000
            results.append({'date':date, 'profit': day_profit})
            
            final_total += day_profit
        results = pd.DataFrame(results); results.set_index('date', inplace=True)
        return final_total > 0