import alpaca_trade_api as alp

TRADE_END_HOUR = 16
PIP_DURATION = alp.TimeFrame.Minute
PIP_SECONDS = 60
PIP_OFFSET = 1
PRICE_BUFFER = 0.01
LIVE_BUFFER = .05
S_LIVE_BUFFER = .01
TRADE_START_HOUR = 9
TRADE_START_MINUTE = 35
# TRADE_START_HOUR = round(9 + int((PIP_DURATION*40)/60 / 30))
# TRADE_START_MINUTE = ((60+int(round(int((PIP_DURATION*40)/60))-30)) % 60) + 4

ALLOW_UPDATE = True
PROCESS_BUFFER = 30

GAMBIT_GRACE = 5
GAMBIT_ATTEMPTS = 3