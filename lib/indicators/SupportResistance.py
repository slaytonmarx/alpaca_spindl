from lib.indicators.Indicator import Indicator
from scipy.signal import argrelextrema
import matplotlib.pyplot as plt
import metadata.trade_configs.Globals as gb
import lib.tools.Scrivener as sc
import numpy as np
import pandas as pd

class SupportResistance(Indicator):
    def __init__(self, df:pd.DataFrame, limit_date:pd.Timestamp = None, n:int = 2, r:int = 1):
        self.n, self.r, self.maxima, self.minima = n, r, [], []
        super().__init__(df, limit_date)
        
    def update(self, df:pd.DataFrame):
        super().update(df)
        if not hasattr(self, 'indicator'):
            for index in df.index: self.update_maxima_and_minima(df, index)
            self.maxima_lines, self.minima_lines = self.get_maxima_and_minima_lines(self.df)
        elif self.indicator.index[-1] < self.df.index[-1]:
            self.update_maxima_and_minima(df, index)
            self.maxima_lines, self.minima_lines = self.get_maxima_and_minima_lines(self.df)

    def get_signal(self, index: pd.Timestamp = None):
        index = super().get_signal(index)

        if len(self.maxima_lines) > 0:
            total, maxima_thus_far = 0, len(self.maxima_lines[:index])
            if maxima_thus_far < self.r: return 0
            for i in range(1,self.r+1):
                line = self.maxima_lines[:index].iloc[-i].line
                if self.df.close.loc[index] > line.loc[index]: total += 1
            if total >= self.r: return 1
        if len(self.minima_lines) > 0:
            total, minima_thus_far = 0, len(self.minima_lines[:index])
            if minima_thus_far < self.r: return 0
            for i in range(1,self.r+1):
                line = self.minima_lines[:index].iloc[-i].line
                if self.df.close.loc[index] < line.loc[index]: total += 1
            if total >= self.r: return -1
        return 0

    def get_maxima_and_minima_lines(self, df:pd.DataFrame):
        maxima_lines, minima_lines = [], []
        for i in range(len(self.maxima))[1:]: maxima_lines.append({'time':self.maxima.index[i], 'line':self.draw_line(self.maxima.index[i-1], self.maxima.index[i], self.maxima, df)})  
        for i in range(len(self.minima))[1:]: minima_lines.append({'time':self.minima.index[i], 'line':self.draw_line(self.minima.index[i-1], self.minima.index[i], self.minima, df)})
        maxima_lines, minima_lines = pd.DataFrame(maxima_lines), pd.DataFrame(minima_lines)
        if len(maxima_lines) > 0: maxima_lines.set_index('time',inplace=True)
        if len(minima_lines) > 0: minima_lines.set_index('time',inplace=True)
        return maxima_lines, minima_lines

    def update_maxima_and_minima(self, df:pd.Series, index:pd.DatetimeIndex = None):
        '''Returns two lists of the local maxima and minima'''
        if not index: index = df.index[-1]
        #maxima = df.close.iloc[argrelextrema(df.close[:index].values, np.greater_equal, order=self.n)[0]].iloc[:-1]
        #minima = df.close.iloc[argrelextrema(df.close[:index].values, np.less_equal, order=self.n)[0]].iloc[:-1]
        '''What do we actually want each time? We want all of the maxima and minima up to this point, and each time we call it to add whatever else was discovered from the last time we called it'''
        if not hasattr(self, 'start_search'): self.start_search = df.index[0]
        for index in df[self.start_search:].index:
            '''Search through the given indexes'''
            span = self.df[index-pd.DateOffset(minutes=self.n):index]
            if span.high.idxmax() == index:
                if df.loc[index].close < df.loc[index].open: continue
                if len(self.maxima) == 0: self.maxima = pd.Series([span.high.loc[index]], index=[index])
                else: self.maxima.loc[index] = span.high.loc[index]
            elif span.low.idxmin() == index:
                if df.loc[index].close > df.loc[index].open: continue
                if len(self.minima) == 0: self.minima = pd.Series([span.low.loc[index]], index=[index])
                else: self.minima.loc[index] = span.low.loc[index]
        self.start_search = df.index[-1]
            
    def check_extrema(self, index):
        return None
            
    def get_distance(self, index1:pd.DatetimeIndex, index0:pd.DatetimeIndex):
        return (index1 - index0).seconds/60

    def draw_line(self, p1:pd.DatetimeIndex, p2:pd.DatetimeIndex, line_series:pd.Series, df:pd.DataFrame):
        a, b = line_series.loc[p1], line_series.loc[p2]
        slope = (b-a)/self.get_distance(p2, p1)
        offset = a - (self.get_distance(p1, df.index[0]) * slope)

        line = []
        for i in range(len(df)): line.append(i*slope + offset)
        line = pd.Series(line); line.index = df.index
        return line
    
    def plot(self):
        for index in self.maxima_lines.index:
            line = self.maxima_lines.loc[index].line[index-pd.DateOffset(minutes = 10):index+pd.DateOffset(minutes = 10)]
            plt.plot(line.index, line, color='orange', lw=.25)
        for index in self.minima_lines.index:
            line = self.minima_lines.loc[index].line[index-pd.DateOffset(minutes = 10):index+pd.DateOffset(minutes = 10)]
            plt.plot(line.index, line, color='blue', lw=.25)
        plt.scatter(self.maxima.index, self.maxima, c='orange')
        plt.scatter(self.minima.index, self.minima, c='blue')