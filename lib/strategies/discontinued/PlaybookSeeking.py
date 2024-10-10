import sys
from lib.Portfolio import Portfolio; sys.path.append('../..')
from lib.Strategy import SelectionStrategy, Strategy
import lib.Toolbox as tb
import lib.TimeKeeper as tk
import pandas as pd
import matplotlib.pyplot as plt

class PlaybookSeeking(Strategy):
    '''Strategy where we get an average of the data then buy when below that average and sell when above.'''
    def __init__(self, symbol: str, port: Portfolio, context: SelectionStrategy, date: pd.DatetimeIndex = None,
                 archive_data:pd.DataFrame = None, tune:bool = False):
        super().__init__(symbol, port, context, date, archive_data, tune,
                         tuning_variables=[['BOL_DEV',[.75, 1, 1.5]],
                                           ['MINUTE_WAIT',[10,15,30]]])
        self.trailing_data = pd.DataFrame([self.data.iloc[-1]])
        self.still_hustling = True
        self.signal_history = []
        self.playbook = self.Playbook()
        self.signal = 0
        
    def trade_command(self, index:pd.DatetimeIndex):
        '''Says to buy when our value is below our average and sell when above'''
        if len(self.data) == 1: return

        self.update_values(index)

        order = self.calculate_order(index)

        self.get_trade_type(index)
        
        if self.failsafes(index): return
        
        now = tk.now()
        buffer = self.calculate_buffer(index)
        if len(self.active_orders) > 0:
            if not self.has_stock(): self.clear_orders(True)
            return
        if self.last_buy: print(self.has_stock(), index.minute, pd.to_datetime(self.last_buy.created_at).minute, self.has_stock() and self.last_buy and index.minute > pd.to_datetime(self.last_buy.created_at).minute)
        if self.has_stock():#self.last_buy and index.minute != pd.to_datetime(self.last_buy.created_at).minute:
            if self.get_stock_sign():
                if self.sell_criteria(now): self.add_market_transaction('sell', self.port.get_qty(self.symbol))#, self.port.get_price(self.symbol))
            else:
                if self.shortbuy_criteria(now): self.add_market_transaction('shortbuy', self.port.get_qty(self.symbol))#, self.port.get_price(self.symbol))
        elif now.second <= 10:
            if self.signal == 1: self.add_limit_transaction('buy', order, self.value + buffer)
            elif self.signal == -1: self.add_limit_transaction('shortsell', order, self.value - buffer)

    def sell_criteria(self, index: pd.DatetimeIndex):
        #delta = self.trailing_data.open.iloc[-5:].ewm(span=5).mean().diff().iloc[-1]
        #if index.second >= 30 and delta < 0: return True
        if index.second >= 55: return True
        return False
    
    def shortbuy_criteria(self, index: pd.DatetimeIndex):
        #delta = self.trailing_data.open.iloc[-5:].ewm(span=5).mean().diff().iloc[-1]
        #if index.second >= 30 and delta > 0: return True
        if index.second >= 55: return True
        return False
    
    def calculate_buffer(self, index:pd.DatetimeIndex):
        '''Calculates the buffer necessary to keep pace with changing deltas'''
        i = tb.get_i(index, self.data)
        opdel = self.data.open.iloc[i-10:i+1].diff()
        last_delta = opdel.iloc[-1] 
        mean_delta = opdel.iloc[:-1].mean()
        ratio = abs(last_delta/mean_delta)
        if last_delta/mean_delta > 1: return .05
        elif last_delta/mean_delta > .5: return .03
        else: return .01

    def update_values(self, index:pd.DatetimeIndex):
        '''Updates all values that will be used by the trade_command'''
        # last_index = tb.get_previous_index(index, self.data, 1)
        #self.value, self.last_value = self.data.open.loc[index], self.data.open.loc[last_index]
        # self.value = self.data.close.loc[last_index]
        self.value = self.data.open.loc[index]
        self.update_traililng_data(index)

    def update_traililng_data(self, index:pd.DatetimeIndex):
        '''Updates our trailing data so we can better visualize it and use it for future testing'''
        self.trailing_data.loc[tk.now()] = self.data.iloc[-1]
        if index.minute % 10 == 0: tb.save_archive(self.symbol, 'trailing_data', self.trailing_data)

    def calculate_order(self, index:pd.DatetimeIndex):
        '''Returns an integer amount of stock to order when buying/short selling'''
        spending_cap = self.spending_cap
        order = int(spending_cap / self.value / self.conf.ORDER_DIVIDER / self.conf.ALLOCATION_DIVIDER) - 50
        if order < 0: order = 0
        return order

    def get_data(self, interval:str = '1m'):
        self.data = super().get_data(interval, start=self.date)
        return self.data

    def failsafes(self, index):
        #if not self.has_stock() and self.last_buy and index.minute != pd.to_datetime(self.last_buy.created_at).minute: self.last_buy = None
        # if self.last_buy:
        #     if tk.now() >= pd.to_datetime(self.last_buy.created_at) + pd.DateOffset(seconds=120):
        #         if len(self.active_orders) > 0 and self.active_orders[0].type == 'market': return True
        #         self.clear_orders(True)
        #         if self.get_stock_sign(): self.add_market_transaction('sell', self.port.get_qty(self.symbol)); return True
        #         else: self.add_market_transaction('shortbuy', self.port.get_qty(self.symbol)); return True

        # Clears if we have a very small amount of straggler stock
        #if self.has_stock() and self.port.get_qty(self.symbol) < 15 and len(self.active_orders) > 0 and index > pd.to_datetime(self.last_buy.created_at) + pd.DateOffset(minutes=5):
            #print('Running a quick clear!')
        #    self.clear_orders(True)
        #    if self.get_stock_sign(): self.add_market_transaction('sell', self.port.get_qty(self.symbol)); return True
        #    else: self.add_market_transaction('shortbuy', self.port.get_qty(self.symbol)); return True
        return False

    def get_trade_type(self, index: pd.DatetimeIndex):
        '''Returns whether the day is up or down based on the trend of the last couple days'''
        i = tb.get_i(index, self.data)
        entries = self.data.iloc[i-5:i]
        self.signal = self.playbook.play(entries)
        self.signal_history.append(self.signal)

    def plot_line(self):
        '''Plots the graph'''
        super().plot_line()
        plt.plot(self.bollinger[self.date:].index, self.bollinger[self.date:].lowband, color='red', lw=.5)
        plt.plot(self.bollinger[self.date:].index, self.bollinger[self.date:].moving_average, color='orange', lw=.5)
        plt.plot(self.bollinger[self.date:].index, self.bollinger[self.date:].highband, color='green', lw=.5)
        plt.show()

    class Playbook():
        '''Class for containing next steps when performing high frequency trading.  Each type of play is a
            unique class with critiria that can be met and an order of priority. When determining our next
            step we run through our plays and choose the play whose criteria is met, and if multiple plays
            are met we select based on priority.
        '''
        def __init__(self):
            self.plays_available = [self.BendToAverage]#, self.InflectionPoint]#, self.WobbleRatio]
            self.plays_made = []
            #self.update_context(data, self.data.index[-1])

        def play(self, entries:pd.DataFrame):
            '''Takes a set of information and determines the next action our trader should perform'''

            ''' We need to formalize this. If we make our decisions based on the open price when we get it
                there will be discrepencies between our training and our live. If we give everything a lag
                of one minute then they'll remain the same(ish)

                Ok, so entries should have everything leading up to THIS minute, the minute we're testing
                for, but not the minute itself.
            '''

            last_entry = entries.iloc[-1]
            last_info = self.Pressure(last_entry)

            choice = None
            for play_type in self.plays_available:
                play = play_type(self, entries, last_entry, last_info)
                if play.decision != None:
                    if not choice: choice = play
                    elif choice.priority < play.priority: choice = play
            if choice:
                self.plays_made.append(choice)
                return choice.decision
            return 0

        class Play():
            def __init__(self, playbook, entries:pd.DataFrame, last_entry:pd.DataFrame, last_info):
                self.book = playbook
                self.entries, self.last_entry, self.last_info = entries, last_entry, last_info
                self.priority = self.set_priority()
                self.decision =  self.criteria()

            def set_priority(self):
                ''

            def criteria(self):
                ''

        class InflectionPoint(Play):
            def set_priority(self):
                return 3
            def criteria(self):
                '''Determines whether the given index is an inflection point given it's surroundings'''
                set_mag = abs(self.entries.close-self.entries.open).mean()
                entry_mag = abs(self.last_entry.close - self.last_entry.open)
                if set_mag * .25 > entry_mag: return 0
                else: return None

        class WobbleRatio(Play):
            def set_priority(self):
                return 3
            def criteria(self):
                if self.last_info.magnitude < (self.last_info.upline + self.last_info.downline) * .1:
                    return 0
                else: return None

        class BendToAverage(Play):
            def set_priority(self):
                return 2
            def criteria(self):
                mav = (self.entries.iloc[-1:].open.mean()+self.last_entry.close)/2
                val = self.last_entry.close

                # pmav = self.entries.iloc[-3:-1].open.mean()
                # pval = self.last_entry.open
                # if pval < pmav and not self.last_info.sign: return -1
                # elif pval > pmav and self.last_info.sign: return 1
                
                if val < mav: prediction = 1
                elif val > mav: prediction = -1
                else: prediction = 0
                return prediction
                    
        class Pressure():
            '''Represents the important information about an entry'''
            def __init__(self, entry:pd.DataFrame):
                positive = entry.open < entry.close
                if positive:
                    upward_pressure = entry.high - entry.close
                    downward_pressure = entry.open - entry.low
                    magnitude = entry.close - entry.open
                # We rose
                else:
                    upward_pressure = entry.high - entry.open
                    downward_pressure = entry.close - entry.low
                    magnitude = entry.open - entry.close
                self.upline, self.downline, self.sign = upward_pressure, downward_pressure, positive
                self.magnitude = magnitude

# trend = tb.get_trend(entries.open)
# if trend > .2 and self.signal == -1: self.signal = 0; print('Signal Trend Mismatch')
# elif trend < -.2 and self.signal == 1: self.signal = 0; print('Signal Trend Mismatch')
# trail_snapshot = self.trailing_data.open.iloc[-3:]
# tdelta = trail_snapshot.diff().ewm(span=5).mean()
# tacc = tdelta.diff()
# if tdelta.iloc[-1] > 0 and tacc.iloc[-1] > 0: self.signal = 1
# elif tdelta.iloc[-1] < 0 and tacc.iloc[-1] < 0: self.signal = -1
# else: self.signal = 0
#print(self.signal, self.value, 'delta',tdelta.iloc[-1],'acc',tacc.iloc[-1])