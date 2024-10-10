from lib.indicators.Indicator import Indicator
import metadata.trade_configs.Globals as gb
import lib.tools.Scrivener as sc
import pandas as pd

class ForebodingWick(Indicator):
    def __init__(self, df:pd.DataFrame):
        super().__init__(df)

    def update(self, df:pd.DataFrame):
        super().update(df)
        if not hasattr(self, 'indicator'):
            self.indicator = self.find_foreboding_wicks(self.df)
        elif self.indicator.index[-1] < self.df.index[-1]:
            self.indicator = sc.easy_concat(self.indicator, self.find_foreboding_wicks(self.df[self.indicator.index[-1]-pd.DateOffset(seconds=gb.PIP_DURATION*2):]))
    
    def get_signal(self, index:pd.Timestamp = None):
        index = super().get_signal(index)
        span = self.indicator.loc[index-pd.DateOffset(seconds=gb.PIP_DURATION*15):index]
        weighed_portends = span.portends_good.iloc[-15:].sum() - span.portends_ill.iloc[-15:].sum()
        if weighed_portends > 0: return 1
        elif weighed_portends < 0: return -1
        else: return 0

    def find_foreboding_wicks(self, df:pd.DataFrame):
        '''Finds wicks which may present a foreboding sign'''
        wick = []
        for index in df.index:
            entry = df.loc[index]
            if (entry.close > entry.open): top_wick, bottom_wick = entry.high - entry.close, entry.open - entry.low
            else: top_wick, bottom_wick = entry.high - entry.open, entry.close - entry.low
            portends_good, portends_ill = bottom_wick > (top_wick * 2), top_wick > (bottom_wick * 2)
            wick.append({'index':index, 'portends_good':portends_good, 'portends_ill': portends_ill})
        return pd.DataFrame(wick).set_index('index')