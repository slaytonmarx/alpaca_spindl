from lib.indicators.Indicator import Indicator
import matplotlib.pyplot as plt
import metadata.trade_configs.Globals as gb
import lib.tools.Scrivener as sc
import pandas as pd

class RSI(Indicator):
    def __init__(self, df:pd.DataFrame, rsi_period:int = 14, strictness:int = 30):
        self.rsi_period, self.strictness = rsi_period, strictness
        super().__init__(df)
    
    def update(self, df:pd.DataFrame):
        '''Updates the rsi'''
        super().update(df)
        if not hasattr(self, 'indicator'): self.indicator = self.get_rsi(self.df)
        elif self.indicator.index[-1] < self.df.index[-1]:
            self.indicator = sc.easy_concat(self.indicator, self.get_rsi(self.df[self.indicator.index[-1]-pd.DateOffset(seconds=gb.PIP_SECONDS*(self.rsi_period+1)):]))

    def get_signal(self, index: pd.Timestamp = None):
        index = super().get_signal(index)
        if self.indicator.loc[:index].iloc[-1] < self.strictness: return 1
        if self.indicator.loc[:index].iloc[-1] > (100 - self.strictness): return -1
        else: return 0

    def get_rsi(self, data:pd.DataFrame, column:str = 'close'):
        '''Adds the rsi value to the data and returns it'''
        delta = data[column].diff()
        delta.dropna(inplace=True)

        delta_pos = delta.copy(); delta_pos[delta_pos<0] = 0
        delta_neg = delta.copy(); delta_neg[delta_neg>0] = 0

        delta.equals(delta_pos+delta_neg)

        avg_up = delta_pos.rolling(self.rsi_period).mean()
        avg_down = delta_neg.rolling(self.rsi_period).mean().abs()
        avg_up.dropna(inplace=True)
        avg_down.dropna(inplace=True)
        
        return (100 * avg_up / (avg_up + avg_down))#.ewm(span=3).mean()
    
    def plot(self, date:pd.Timestamp = None):
        if not date: date = self.df.index[0]
        for index in self.df[date:].index:
            signal = self.get_signal(index)
            if signal == 1: plt.axvline(index, color='green', lw=1, alpha=.1)
            elif signal == -1: plt.axvline(index, color='red', lw=1, alpha=.1)