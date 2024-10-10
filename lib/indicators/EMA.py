from lib.indicators.Indicator import Indicator
import metadata.trade_configs.Globals as gb
import lib.tools.Toolbox as tb
import lib.tools.Scrivener as sc
import numpy as np
import pandas as pd

class EMA(Indicator):
    def __init__(self, df:pd.DataFrame, ema1:int = 13, ema2:int = 21, ema3:int = 55):
        self.l1, self.l2, self.l3 = ema1, ema2, ema3
        super().__init__(df)
    
    def update(self, df:pd.DataFrame):
        '''Updates the rsi'''
        super().update(df)
        if not hasattr(self, 'ema0'):
            self.ema0 = tb.get_ema(df.close, 2)
            self.ema1 = tb.get_ema(df.close, self.l1)
            self.ema2 = tb.get_ema(df.close, self.l2)
            self.ema3 = tb.get_ema(df.close, self.l3)
            self.bull1 = self.ema1 < self.ema0
            self.bull2 = self.ema2 < self.ema0
            self.bull3 = self.ema3 < self.ema0
        elif self.ema0.index[-1] < self.df.index[-1]:
            span = self.df.iloc[tb.get_i(self.ema0.index[-1], self.df) - (self.l3+15):]
            span_ema0 = tb.get_ema(span.close, 2)
            span_ema1 = tb.get_ema(span.close, self.l1)
            span_ema2 = tb.get_ema(span.close, self.l2)
            span_ema3 = tb.get_ema(span.close, self.l3)
            span_bull1 = span_ema1 < span_ema0
            span_bull2 = span_ema2 < span_ema0
            span_bull3 = span_ema3 < span_ema0

            # self.ema0 = tb.get_ema(span.close, 2)
            # self.ema1 = tb.get_ema(span.close, 13)
            # self.ema2 = tb.get_ema(span.close, 21)
            # self.ema3 = tb.get_ema(span.close, 55)
            # self.bull1 = self.ema1 < self.ema0
            # self.bull2 = self.ema2 < self.ema0
            # self.bull3 = self.ema3 < self.ema0
            
            self.ema0 = sc.easy_concat(self.ema0, span_ema0[self.ema0.index[-1]:])
            self.ema1 = sc.easy_concat(self.ema1, span_ema1[self.ema1.index[-1]:])
            self.ema2 = sc.easy_concat(self.ema2, span_ema2[self.ema2.index[-1]:])
            self.ema3 = sc.easy_concat(self.ema3, span_ema3[self.ema3.index[-1]:])
            self.bull1 = sc.easy_concat(self.bull1, span_bull1[self.bull1.index[-1]:])
            self.bull2 = sc.easy_concat(self.bull2, span_bull2[self.bull2.index[-1]:])
            self.bull3 = sc.easy_concat(self.bull3, span_bull3[self.bull3.index[-1]:])
            
    def get_signal(self, index: pd.Timestamp = None):
        index = super().get_signal(index)
        if self.bull1.loc[index] and self.bull2.loc[index] and self.bull3.loc[index]: return 1
        if not self.bull1.loc[index] and not self.bull2.loc[index] and not self.bull3.loc[index]: return -1
        else: return 0

    def sum_bulls(self, index: pd.Timestamp = None):
        return (int(self.bull1.loc[index])+int(self.bull2.loc[index])+int(self.bull3.loc[index]))