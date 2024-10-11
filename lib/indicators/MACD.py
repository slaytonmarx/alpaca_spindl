from lib.indicators.Indicator import Indicator
import metadata.trade_configs.Globals as gb
import lib.tools.Scrivener as sc
import pandas as pd

class MACD(Indicator):
    def __init__(self, df:pd.DataFrame, short:int = 12, long:int = 26, smoothing:int = 9):
        self.short, self.long, self.smoothing = short, long, smoothing
        super().__init__(df)
    
    def update(self, df:pd.DataFrame):
        '''Updates the rsi'''
        super().update(df)
        if not hasattr(self, 'indicator'): self.indicator = self.get_macd(self.df)
        elif self.indicator.index[-1] < self.df.index[-1]:
            self.indicator = sc.easy_concat(self.indicator, self.get_macd(self.df[self.indicator.index[-1]-pd.DateOffset(seconds=60*(self.long*3)):]))

    def get_signal(self, index: pd.Timestamp = None):
        index = super().get_signal(index)
        if self.indicator.loc[:index].iloc[-2].macd_h < 0 and self.indicator.loc[:index].iloc[-1].macd_h > 0: return 1
        elif self.indicator.loc[:index].iloc[-2].macd_h > 0 and self.indicator.loc[:index].iloc[-1].macd_h < 0: return -1
        else: return 0

    def get_macd(self, data:pd.DataFrame):
        '''Returns the data with the macd values for the given parameters added as columns'''
        k = data.close.ewm(span=self.short, adjust=False, min_periods=self.short).mean()
        d = data.close.ewm(span=self.long, adjust=False, min_periods=self.long).mean()
        macd = k - d
        macd_s = macd.ewm(span=self.smoothing, adjust=False, min_periods=self.smoothing).mean()
        macd_h = macd - macd_s
        macd_hd = macd_h.diff()
        df = pd.concat([macd, macd_s, macd_h, macd_hd], axis=1)
        df.columns=['macd','macd_s','macd_h','macd_hd']
        return df