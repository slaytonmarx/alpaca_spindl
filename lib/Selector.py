import pandas as pd

class Selector:
    '''Uses various methods to determine what symbols are viable for experimentation on a given day'''
    def __init__(self, symbol:str, date:pd.Timestamp, strategy):
        self.symbol, self.date, self.strategy, self.strategy_name = symbol, date, strategy, strategy.__name__
    
    def is_valid(self):
        '''Tests our symbol for validity based on it's criteria'''
        return False