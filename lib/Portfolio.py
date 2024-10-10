import os.path as path
import metadata.trade_configs.Globals as gb
import lib.tools.Broker as br
import lib.tools.TimeKeeper as tk
import pandas as pd
import math
import json

class Portfolio:
    '''Simple class to keep track of our stock, and perform bookkeeping on it. Acts as an interface to the brokerage.
    '''
    def __init__(self, api):
        self.api, self.positions = api, {}
        self.data_api = br.paper_api()
        if not api: self.cash, self.orders = 100000, {}; self.day_start_cash = self.cash
        else: self.cash = (float(self.api.get_account().buying_power))

    def get_qty(self, symbol:str):
        '''Gets the value of all stocks of the given name in the portfolio'''
        if self.api: self.positions = {position.symbol:position for position in self.api.list_positions()}
        if symbol not in self.positions: return 0
        else: return int(self.positions[symbol].qty)
    
    def get_day_change(self):
        if self.api:
            account = self.api.get_account()
            return float(account.equity) - float(account.last_equity)
        else: return self.cash - self.day_start_cash

    def get_price(self, symbol:str):
        '''Gets the qty of all of the given stock in the portfolio'''
        if self.api: self.positions = {position.symbol:position for position in self.api.list_positions()}
        return float(self.positions[symbol].avg_entry_price) if symbol in self.positions else 0
    
    def calculate_live_price(self, symbol:str, index:pd.DatetimeIndex = None):
        if self.api:
            trades = self.api.get_trades(symbol, start=tk.dto_time(tk.now().round('s')-pd.DateOffset(seconds=2)), end=tk.dto_time(tk.now().round('s'))).df
            if len(trades) == 0: self.api.get_trades(symbol, start=tk.dto_time(tk.now().round('s')-pd.DateOffset(minutes=2)), end=tk.dto_time(tk.now().round('s'))).df
        elif index:
            index = index + pd.DateOffset(minutes=1)
            trades = self.data_api.get_trades(symbol, start=tk.dto_time(index.round('s')-pd.DateOffset(seconds=2)), end=tk.dto_time(index.round('s')+pd.DateOffset(seconds=gb.PIP_OFFSET))).df
            if len(trades) == 0: trades =  self.data_api.get_trades(symbol, start=tk.dto_time(index.round('s')-pd.DateOffset(minutes=2)), end=tk.dto_time(index.round('s')+pd.DateOffset(seconds=gb.PIP_OFFSET))).df
            # if not hasattr(self, 'trades'): self.trades = sc.update_trades(symbol, self.date) if gb.ALLOW_UPDATE else sc.get_trade_archive(symbol, self.date)
            # trades = self.trades[index-pd.DateOffset(seconds=2):index]
        price = trades.price.iloc[-1]#.mean()
        #delta = prices.diff()#.ewm(span=10).mean()
        # return round(trades.price.iloc[-1]+ delta.iloc[-1],2)
        return round(price, 2)
    
    def has_stock(self, symbol:str = None):
        '''Returns whether we still have stock in our portfolio. If a symbol is given, checks if that stock is in the portfolio'''
        if self.api: self.positions = {position.symbol:position for position in self.api.list_positions()}
        if symbol: return symbol in self.positions and abs(int(self.positions[symbol].qty)) > 0
        else: return len(self.positions) > 0

    def get_stock_sign(self, symbol:str):
        '''Returns whether we are holding a short, or normal stock. Returns True for positive and False for negative'''
        if self.api: self.positions = {position.symbol:position for position in self.api.list_positions()}
        return int(self.positions[symbol].qty) > 0
    
    def get_stock_value(self, symbol):
        '''Returns the value currently invested in a given stock based on it's avg_entry_price'''
        if self.api: self.positions = {position.symbol:position for position in self.api.list_positions()}
        if not symbol in self.positions: return 0
        position = self.positions[symbol]
        return position.qty * position.avg_entry_price
    
    def get_last_order(self, symbol:str):
        '''Finds the order which populated the position of the given symbol'''
        if symbol not in self.positions: return None
        position = self.positions[symbol]

        order_list = self.api.list_orders(symbol, limit=4) if self.api else self.orders[symbol][::-1]
        for order in order_list:
            if position.side == 'long' and order.side == 'buy': break
            if position.side == 'short' and order.side == 'sell': break
        
        # Universal Formatting
        if not order.filled_avg_price: order.filled_avg_price = 0.0
        order.filled_avg_price = float(order.filled_avg_price)
        order.created_at = pd.to_datetime(order.created_at).tz_convert('America/New_York').floor('s')
        order.qty = int(order.qty)
        return order
    
    def get_immediate_order(self, symbol:str):
        '''Finds the order which populated the position of the given symbol'''
        if symbol not in self.orders: return None
        order_list = self.api.list_orders(symbol, limit=4) if self.api else self.orders[symbol][::-1]
        return order_list[0]
    
    def get_last_order_by_side(self, symbol:str, side:str):
        order_list = self.api.list_orders(symbol, limit=4) if self.api else self.orders[symbol][::-1]
        for order in order_list:
            if side == order.side: break
            if side == order.side: break
        
        # Universal Formatting
        order.filled_avg_price = float(order.filled_avg_price)
        order.created_at = pd.to_datetime(order.created_at).tz_convert('America/New_York').floor('s')
        order.qty = int(order.qty)
        return order
        
    def historic_order(self, strategy, index:pd.DatetimeIndex, trade_type:str, quantity:int, price:float = None):
        '''Adds the stock position to our position list during backtesting'''
        symbol = strategy.symbol
                    
        if not symbol in self.orders: self.orders[symbol] = []

        match trade_type:
            case 'buy':
                if symbol in self.positions: return # We already have a position open, so no buy
                self.positions[symbol] = self.Position(price, quantity, 'buy', symbol) # Add New Position     
                self.orders[symbol].append(self.Order(index, price, quantity, 'buy', symbol)) # Add to Orders
                total_change = -price*quantity
            case 'shortsell':
                if symbol in self.positions: return # We already have a position open, so no shortsell
                self.positions[symbol] = self.Position(price, quantity, 'sell', symbol) # Add New Position
                self.orders[symbol].append(self.Order(index, price, quantity, 'shortsell', symbol)) # Add to Orders
                total_change = -price*quantity
            case 'sell':
                if symbol not in self.positions: return # We don't have a position open, so no sell
                position = self.positions[symbol] # Get the position that's open
                if quantity == abs(self.positions[symbol].qty): del self.positions[symbol] # Remove Position
                else: self.positions[symbol].qty -= quantity
                self.orders[symbol].append(self.Order(index, price, quantity, 'sell', symbol)) # Add Order
                total_change = quantity * price
            case 'shortbuy':
                if symbol not in self.positions: return # We don't have a position open, so no sell
                position = self.positions[symbol] # Get the position that's open
                total_change = abs(position.qty) * price
                prev_order = self.get_last_order(strategy.symbol) 
                profit = (((prev_order.filled_avg_price) - (price)) * abs(quantity))
                total_change = (abs(quantity)*prev_order.filled_avg_price) + profit
                if abs(quantity) == abs(self.positions[symbol].qty): del self.positions[symbol] # Remove Position
                else: self.positions[symbol].qty += abs(quantity)
                self.orders[symbol].append(self.Order(index, price, quantity, 'shortbuy', symbol)) # Add Order
        self.cash += total_change
        return self.orders[symbol][-1]

    def __str__(self):
        s = f'PROFIT: {round(self.get_day_change(),2)},\npositions:\n{self.positions}'
        return s
    
    class Position():
        '''Backtesting class to simulate brokerage positions'''
        def __init__(self, avg_entry_price:float, qty:int, side:str, symbol: str):
            self.avg_entry_price, self.qty, self.side, symbol = avg_entry_price, qty, side, symbol
            if self.side == 'buy': self.side = 'long'
            elif self.side == 'sell':
                self.side = 'short'
                self.qty *= -1
    
    class Order():
        '''Backtesting class to simulate brokerage Order'''
        def __init__(self, created_at:pd.DatetimeIndex, filled_avg_price:float, qty:int, side:str, symbol:str):
            self.created_at, self.limit_price, self.filled_avg_price, self.qty, symbol = created_at, filled_avg_price, filled_avg_price, qty, symbol
        
            match side:
                case 'buy':
                    self.side = 'buy'
                    self.mark = 1
                    #self.filled_avg_price += .1
                case 'sell':
                    self.side = 'sell'
                    self.mark = -1
                case 'shortsell':
                    self.side = 'sell'
                    self.mark = 2
                    #self.filled_avg_price -= .1
                case 'shortbuy':
                    self.side = 'buy'
                    self.mark = -2
        
        def __str__(self):
            return f'{self.created_at} {self.side} {self.qty} {self.filled_avg_price}'