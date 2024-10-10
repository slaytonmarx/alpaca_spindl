from lib.Portfolio import Portfolio
import metadata.trade_configs.Globals as gb
import lib.tools.TimeKeeper as tk
import lib.tools.Logger as log
import lib.tools.Broker as br
import pandas as pd
import math

class Gambit:
    def __init__(self, port:Portfolio, symbol:str, price:float, qty:int, trade_code:str, msg:str = '', failsafe:bool = False, start_index:pd.DatetimeIndex = tk.now(), buffer:float = gb.LIVE_BUFFER):
        self.port, self.symbol, self.initial_price, self.qty, self.trade_code, self.msg, self.failsafe, self.index = port, symbol, price, abs(int(qty)), trade_code, msg, failsafe, start_index
        self.api, self.grace, self.attempts, self.buffer = self.port.api, gb.GAMBIT_GRACE, gb.GAMBIT_ATTEMPTS, buffer
        self.play()

    def play(self):
        '''Our first and simplest gambit. Makes a limit order and attempts to follow
            through with it, changing the order if it seems out of reach.
        '''
        if 'sell' in self.trade_code: self.qty *= -1
        initial_qty = self.port.get_qty(self.symbol)
        target_qty = initial_qty + self.qty
        self.order = self.monitor_order(self.generate_order('limit', abs(self.qty), self.initial_price))

        for i in range(self.attempts):
            tk.wait(3)
            print('Stock we have:', self.port.get_qty(self.symbol),'\tStock we want:',target_qty)
            if (('buy' in self.trade_code and self.port.get_qty(self.symbol) >= target_qty)
                or ('sell' in self.trade_code and self.port.get_qty(self.symbol) <= target_qty)
                    or self.order.status == 'filled'): break
            print('\tAttempt Failed, Strike Again, Amen')
            print('partial failure',
                  '\n\tinitial desired_qty',self.qty,
                  '\n\ttarget qty',target_qty,
                  '\n\tqty in port', self.port.get_qty(self.symbol),
                  '\n\thow much we think we need to buy/sell',(target_qty - self.port.get_qty(self.symbol)))
            self.qty = abs(target_qty - self.port.get_qty(self.symbol))

            if self.qty == 0: break
            price = round(self.port.calculate_live_price(self.symbol), 2)
            print('NEW PRICE', price)
            self.order = self.monitor_order(self.generate_order('limit', abs(self.qty), price))
        self.log_order(self.order, 'limit', self.initial_price, (initial_qty + self.port.get_qty(self.symbol)), self.msg)
        self.cancel_open_order()

    def generate_order(self, market_or_limit:str, qty:int, price:float = 0, cancel_open:bool = True):
        '''Generates the order of the given type. Cancels other orders for this stock'''
        if cancel_open: self.cancel_open_order()

        side, qty, price = self.format_transaction(qty, price)
        buffer = -self.buffer if 'sell' in side else self.buffer
        try:
            order = self.format_order(
                (self.api.submit_order(symbol=self.symbol,qty=round(qty),side=side,limit_price=round(price+buffer,2),type=market_or_limit,time_in_force='day')) if market_or_limit == 'limit'
                else self.api.submit_order(symbol=self.symbol, qty=qty, side=side, type=market_or_limit, time_in_force='day'))
            if market_or_limit == 'market':
                tk.wait(5)
                order = self.format_order(self.api.get_order(order.id))
        except Exception as e:
            print('ERROR OCCURED', str(e))
            if e._error['message'] == 'insufficient buying power':
                return self.generate_order(market_or_limit, int(qty - 10), round(price,2), False)
        return order
    
    def monitor_order(self, order):
        '''Monitors the given order to verify whether it's been filled or not'''
        for i in range(self.grace):
            order = self.api.get_order(order.id)
            if order.status == 'filled': break
            else: tk.wait(1)
        if order.status != 'filled' and order.status != 'partially_filled':
            order.status = 'incomplete'
        return self.format_order(order)
            
    def cancel_open_order(self):
        '''Cancels any open order of this stock'''
        try:
            last_orders = self.api.list_orders(self.symbol, limit=5)
            for last_order in last_orders:
                if last_order.canceled_at or last_order.status == 'filled': continue
                self.api.cancel_order(last_order.id)
                print('cancelled',last_order.id)
            tk.wait(2)
        except Exception as e: print(e)

    def format_transaction(self, qty:int, price:float):
        match self.trade_code:
            case 'buy':
                if (self.port.cash < qty * price or (self.port.has_stock(self.symbol) and not self.port.get_stock_sign(self.symbol))):
                    self.log_error(qty, price, 'Insufficient Cash for buy order or has short position'); raise Exception('could not initilialize order')
                price = math.ceil(price*100)/100
                side = 'buy'
            case 'sell':
                side = 'sell'
                price = math.ceil(price*100)/100
            case 'shortsell':
                if (self.port.cash < qty * price or (self.port.has_stock(self.symbol) and self.port.get_stock_sign(self.symbol))):
                    self.log_error(qty, price, 'Insufficient Cash for shortsell order or has long position'); raise Exception('could not initilialize order')
                price = math.floor(price*100)/100
                side = 'sell'
            case 'shortbuy':
                side = 'buy'
                price = math.floor(price*100)/100
            case _:
                self.log_error(qty, price, 'Incompatible trade_code'); raise Exception('could not initilialize order')
        return [side, abs(qty), round(price,2)]

    def format_order(self, order):
        '''Formats an order from the brokerage with the correct data types for our usage'''
        if not order.filled_avg_price: order.filled_avg_price = 0
        order.filled_avg_price = float(order.filled_avg_price)
        order.created_at = pd.to_datetime(order.created_at).tz_convert('America/New_York').floor('min')
        order.qty = int(order.qty)
        order.filled_qty = int(order.filled_qty)
        return order
    
    def log_order(self, order, limit_or_market:str, target_price:float, qty:int, msg:str):
        '''Logs the order using the unique information of the gambit'''
        if order:
            order_price = float(order.filled_avg_price)
            self.profit = self.get_order_profit(order_price, qty)
            order_log =  {'status':order.status, 'type': limit_or_market,
                    'side': self.trade_code.upper(),
                    'filled_price': order_price,
                    'target_price': target_price,
                    'delta_price': order_price-target_price,
                    'qty':qty, 'profit': self.profit,
                    'note':msg}
        else: order_log = {'status':'uninitialized', 'type': limit_or_market,
                    'side': self.trade_code.upper(),
                    'filled_price': 0,
                    'target_price': target_price,
                    'delta_price': 0-target_price,
                    'qty':qty, 'profit': 0,
                    'note':msg,
                    'delta_High':0,'delta_Low': 0,'delta_Open': 0}
        log.log(self.api, order.created_at,
                self.symbol, 'ORDERS', order_log)
        print('LOG CREATED')
            
    def log_error(self, qty:int, price:float, msg:str):
        '''Logs an attempted order that failed and notes the reason'''
        log.log(self.api, self.index.round(str(gb.PIP_DURATION)+'s'),
                self.symbol, 'ORDERS',
                {'status':'uninitialized', 'type': 'uninitialized',
                 'side': self.trade_code.upper(),
                 'filled_price': 0,
                 'target_price': price,
                 'delta_price': 0,
                 'qty':qty, 'profit': None,
                 'note':msg,
                 'delta_High': 0,'delta_Low': 0,'delta_Open': 0})
        print('LOG CREATED')

    def get_order_profit(self, clear_price:float, qty:int):
        '''Calculates the profit for sell and shortbuy orders. If this order is buy or shortsell it will simply return 0'''
        try:
            if self.trade_code == 'sell': return (clear_price - self.port.get_last_order_by_side(self.symbol, 'buy').filled_avg_price)*qty
            elif self.trade_code == 'shortbuy': return (self.port.get_last_order_by_side(self.symbol, 'sell').filled_avg_price - clear_price)*qty
            else: return 0
        except:
            return 0
        

    # def setup_old(self):
    #     '''Sets up the gambit to be run, running preliminary error checking, setting important values, and ensuring correct formatting'''
    #     self.prior_qty = self.port.get_qty(self.symbol) if self.symbol in self.port.positions else 0
    #     self.target_qty = self.prior_qty - self.qty if 'sell' in self.trade_code else self.prior_qty + self.qty
    #     if 'sell' in self.trade_code: self.buffer *= -1
    #     self.initial_price = self.initial_price + self.buffer
    #     self.final_order = None

    #     # Initial Validation
    #     if self.port.get_qty(self.symbol) == 0 and (self.trade_code == 'shortbuy' or self.trade_code == 'sell'): self.log_error(self.qty, 0, 'Attempted clear action ['+self.trade_code+'] on empty symbol'); return False
    #     elif self.port.get_qty(self.symbol) < 0 and not 'short' in self.trade_code: self.log_error(self.qty, 0, 'Attempted to shorrt when actively longing'); return False
    #     elif self.port.get_qty(self.symbol) > 0 and 'short' in self.trade_code: self.log_error(self.qty, 0, 'Attempted to long when actively shorting'); return False
    #     # self.log_order(None, self.trade_code, self.initial_price, int(self.qty), 'ATTEMPTING ' + self.msg)
    #     return True

    # def play_old(self):
    #     '''Our first and simplest gambit. Makes a limit order and attempts to follow
    #         through with it, changing the order if it seems out of reach.
    #     '''
    #     #try:
    #     for attempt in range(1, self.attempts+1):
    #         target_price = self.strat.calculate_live_price() + self.buffer if attempt > 1 else self.initial_price#*attempt
    #         if self.check_completion(): break
    #         if self.disengage(target_price): self.msg+=' DISENGAGED'; break
    #         print('\tStarting attempt',attempt,'at',target_price)
    #         self.orders = self.monitor_order(self.generate_orders('limit', self.qty, target_price))
    #         #if self.orders.status != 'filled' and self.port.get_qty(self.symbol) != self.prior_qty: self.qty = abs(int(self.port.get_qty(self.symbol)) - self.target_qty)
    #     #if self.failsafe and not self.check_completion(): self.order = self.generate_orders('market', self.qty)
    #     self.cancel_open_order()
    #     self.log_order(self.orders[0], self.order.type, target_price, int(self.orders[0].filled_qty), self.msg)
    #     self.final_order = self.order
    #     return self.order
    #     # except Exception as e:
    #     #    print(e)

    # def track(self):
    #     '''Tracks the current movement of the price to ensure that, if the price is falling, we don't buy just yet, and likewise
    #         if the price is rising, we don't sell immediately
    #     '''
    #     hold = 1
    #     df = self.strat.get_data('1m').iloc[-1:].open
    #     for i in range(3):
    #         df.loc[tk.now()] = self.strat.get_data('1m').iloc[-1].open
    #         tk.wait(hold)
    #     initial_d = df.diff().ewm(span=len(df)).mean().iloc[-1]
    #     #print('our d',initial_d)
    #     if initial_d == 0: return
    #     elif 'buy' in self.trade_code:
    #         while initial_d <= 0:
    #             df.loc[tk.now()] = self.strat.get_data('1m').iloc[-1].open
    #             tk.wait(hold)
    #             initial_d = df.diff().ewm(span=len(df)).mean().iloc[-1]
    #             #print(tk.now(), initial_d)
    #     elif 'sell' in self.trade_code:
    #         while initial_d >= 0:
    #             df.loc[tk.now()] = self.strat.get_data('1m').iloc[-1].open
    #             tk.wait(hold)
    #             initial_d = df.diff().ewm(span=len(df)).mean().iloc[-1]
    #             #print(tk.now(), initial_d)

    # def generate_orders(self, market_or_limit:str, qty:int, price:float = 0):
    #     '''Generates the order of the given type. Cancels other orders for this stock'''
    #     self.cancel_open_order()

    #     side, qty, price = self.format_transaction(qty, price)
    #     orders = []
    #     try:
    #         for i in range(1, 5+1):
    #             order = self.format_order(
    #                 (self.api.submit_order(symbol=self.strat.symbol,qty=round(qty/5),side=side,limit_price=round(price-(self.buffer/i),2),type=market_or_limit,time_in_force='day')) if market_or_limit == 'limit'
    #                 else self.api.submit_order(symbol=self.strat.symbol, qty=qty, side=side, type=market_or_limit, time_in_force='day'))
    #             orders.append(order)
    #             if market_or_limit == 'market':
    #                 tk.wait(5)
    #                 order = self.format_order(self.api.get_order(order.id))
    #         return orders
    #     except Exception as e:
    #         if e._error['message'] == 'insufficient buying power':
    #             return self.generate_orders(market_or_limit, int(qty/2), price)



    # def check_completion(self):
    #     '''Checks the brokerage to see whether we've completed our order, using the position qty for context'''
    #     self.cancel_open_order()
    #     print('checking order start!',self.port.get_qty(self.symbol), self.target_qty)
    #     if self.port.get_qty(self.symbol) == self.target_qty:
    #         return True
    #     return False

    # def disengage(self, target_price:float):
    #     '''Checks whether the given price has gotten out of hand, and shouldn't be pursued'''
    #     if 'buy' in self.trade_code: return self.initial_price + 1 < target_price
    #     elif 'sell' in self.trade_code: return self.initial_price - 1 > target_price

    # def format_transaction(self, qty:int, price:float):
    #     match self.trade_code:
    #         case 'buy':
    #             if (self.strat.port.cash < qty * price or (self.strat.has_stock() and not self.strat.get_stock_sign())):
    #                 self.log_error(qty, price, 'Insufficient Cash for buy order or has short position'); raise Exception('could not initilialize order')
    #             price = math.ceil(price*100)/100
    #             side = 'buy'
    #         case 'sell':
    #             side = 'sell'
    #             price = math.ceil(price*100)/100
    #         case 'shortsell':
    #             if (self.strat.port.cash < qty * price or (self.strat.has_stock() and self.strat.get_stock_sign())):
    #                 self.log_error(qty, price, 'Insufficient Cash for shortsell order or has long position'); raise Exception('could not initilialize order')
    #             price = math.floor(price*100)/100
    #             side = 'sell'
    #         case 'shortbuy':
    #             side = 'buy'
    #             price = math.floor(price*100)/100
    #         case _:
    #             self.log_error(qty, price, 'Incompatible trade_code'); raise Exception('could not initilialize order')
    #     return [side, abs(qty), round(price,2)]

    # def cancel_open_order(self):
    #     '''Cancels any open order of this stock'''
    #     try:
    #         last_orders = self.api.list_orders(self.strat.symbol, limit=5)
    #         for last_order in last_orders:
    #             if last_order.canceled_at or last_order.status == 'filled': continue
    #             self.api.cancel_order(last_order.id)
    #             print('cancelled',last_order.id)
    #         tk.wait(2)
    #     except Exception as e: print(e)
    
    # def log_error(self, qty:int, price:float, msg:str):
    #     '''Logs an attempted order that failed and notes the reason'''
    #     log.log(self.api, self.strat.data.index[-1].round(str(tk.PIP_DURATION)+'s'),
    #             self.strat.symbol, 'ORDERS',
    #             {'status':'uninitialized', 'type': 'uninitialized',
    #              'side': self.trade_code.upper(),
    #              'filled_price': 0,
    #              'target_price': price,
    #              'delta_price': 0,
    #              'qty':qty, 'profit': None,
    #              'note':msg,
    #              'delta_High': 0,'delta_Low': 0,'delta_Open': 0})
    #     print('LOG CREATED')
        
    # def format_order(self, order):
    #     '''Formats an order from the brokerage with the correct data types for our usage'''
    #     if not order.filled_avg_price: order.filled_avg_price = 0
    #     order.filled_avg_price = float(order.filled_avg_price)
    #     order.created_at = pd.to_datetime(order.created_at).tz_convert('America/New_York').floor('min')
    #     order.qty = int(order.qty)
    #     order.filled_qty = int(order.filled_qty)
    #     return order