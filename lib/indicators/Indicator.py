import pandas as pd

class Indicator:
    def __init__(self, df:pd.DataFrame, limit_date:pd.Timestamp = None):
        self.limit_date = limit_date
        self.update(df)

    def update(self, df:pd.DataFrame):
        '''Updates the indicator's series using it's own df. If the df has changed since inception, instead updates it's series with the new data'''
        self.df = df if not self.limit_date else df[self.limit_date:]

    def get_signal(self, index:pd.Timestamp = None):
        '''Returns the indicator's entry/exit signal. If the indicator suggests upwards movement, returns 1, downwards gives -1, and range gives 0'''
        if not isinstance(index, pd.Timestamp): index = self.df.index[-1]
        return index
    
    def plot(self, date:pd.Timestamp = None):
        '''Plots the indicator on a currently open plt figure'''