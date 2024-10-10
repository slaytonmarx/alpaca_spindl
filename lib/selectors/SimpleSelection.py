from lib.Selector import Selector
import lib.tools.Scrivener as sc
import pandas as pd

class SimpleSelection(Selector):
    '''Simple selector checks whether it's symbol is in a list of "simple_symbols"'''
    
    def __init__(self, name:str, date:pd.Timestamp, strategy):
        super().__init__(name, date, strategy)
    
    def is_valid(self):
        #return self.symbol in sc.load_symbols('active_symbols.txt')
        return True