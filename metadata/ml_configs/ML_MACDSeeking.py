SCONF_VALUE_INFO = {
    'ATR_FACTOR': [[4,12],1],
    'ATR_SELL': [[1,4],1],
    'SHORT': [[3,12],3],
    'LONG': [[12, 24], 3],
    'SMOOTHING': [[6,12], 3]
}

# ML SETTINGS
LOSS_FACTOR = 1
DAY_LOOKBACK = 3 # Should be 5
INITIAL_SEED_COUNT = 5 # Should be 10
CONTENDER_COUNT = 2 # Should be 3
DESCENT_STEPS = 2 # Should be 3

VALUE_RANGES = {pair[0]:pair[1][0] for pair in SCONF_VALUE_INFO.items()}
STEP_SIZES = {pair[0]:pair[1][1] for pair in SCONF_VALUE_INFO.items()}

SHOW_RUNS=False
ALLOW_HIGHRANGE_ADAPTATION=True