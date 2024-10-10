import sys; sys.path.append('../lib/*/*'); sys.path.append('..')
import lib.tools.Broker as br
import lib.tools.TimeKeeper as tk
import pandas as pd
import sys

args = sys.argv
if '-p' in args: api = br.paper_api()
elif '-l' in args: api = br.live_api()
else: api = br.live_api() if input('Watch paper or live? (p/l) ').upper() == 'L' else br.paper_api()
if len(args) > 1: symbol = args[1]
else: symbol = input('What symbol?: ').upper()
# api, symbol = br.paper_api(), 'NVDA'

def get_position(api):
    positions = {position.symbol:position for position in api.list_positions()}
    return positions

def get_alp_price(api, symbol):
    df = api.get_trades(symbol, start=tk.dto_time(tk.now()-pd.DateOffset(seconds=2)), end=tk.dto_time(tk.now())).df
    if len(df) == 0: return None
    return df.price.mean()

last_price = 0

while True:
    price = get_alp_price(api, symbol)
    if not price: price = last_price
    now = tk.now()
    if price == 0: continue
    line = f'{now.hour}:{now.minute} '+symbol+' price '+ str(round(price,2))+'\tDelta: '+str(round(price-last_price,2))
    positions = get_position(api)
    if symbol in positions:
        position = positions[symbol]
        qty, entry_price = int(position.qty), float(position.avg_entry_price)
        profit = round((price-entry_price)*qty,2) if qty > 0 else round((entry_price-price)*abs(qty),2)
        line += '\tqty: '+str(position.qty)+'\tCurrent Value: '+str(profit)
    account = api.get_account()
    day_change = round(float(account.equity) - float(account.last_equity),2)
    line = line+'\tDay Delta: '+str(day_change)
    print(line)
    last_price = price
    tk.wait(1)