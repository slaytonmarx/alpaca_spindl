import pandas as pd
import numpy as np
import sys
import lib.tools.Broker as Broker
import logging
import os
from slack_sdk import WebClient
from lib.RoboTrader import RoboTrader
from lib.tools.Config import Config

# WebClient instantiates a client that can call API methods
# When using Bolt, you can use either `app.client` or the `client` passed to listeners.
client, logger, channel_name = Broker.slack_client()
pd.options.mode.chained_assignment = None
np.seterr(all='ignore', divide=None, over=None, under=None, invalid=None)

args = sys.argv
if '-h' in args or not ('-p' in args or '-l' in args):
    sys.exit('You must specify either paper or live by adding either -l or -p')
if '-l' in args: api, port = Broker.live_api(), 'live' 
else: api, port =  Broker.paper_api(), 'paper'

chosen_symbols = []
if '-t' in args:
    chosen_symbols = args[args.index('-t')+1].upper().split(',')

if '-n' in args:
    chosen_symbols.append('')

config = config=Config('base') if not '-c' in args else Config(args[args.index('-c')+1])

ban = []
if '-b' in args:
    ban = args[args.index('-t')+1].upper().split(',')
    print('These tickers have been banned',ban)

print('Starting Trader')
trader = RoboTrader(api, config=config)
trader.trade_cycle()