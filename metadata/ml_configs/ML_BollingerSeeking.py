SCONF_VALUE_INFO = {
    'BOL_DEV': [[1,2], 1],
    'BOL_EWM': [[3,15], 3],
    'ATR_SELL': [[1,4], 1],
    'ATR_FACTOR': [[6,12],1]
}

# ML SETTINGS
LOSS_FACTOR = 1
DAY_LOOKBACK = 2 # Should be 5
INITIAL_SEED_COUNT = 5 # Should be 10
CONTENDER_COUNT = 1 # Should be 3
DESCENT_STEPS = 2 # Should be 3

VALUE_RANGES = {pair[0]:pair[1][0] for pair in SCONF_VALUE_INFO.items()}
STEP_SIZES = {pair[0]:pair[1][1] for pair in SCONF_VALUE_INFO.items()}

SHOW_RUNS=False
ALLOW_HIGHRANGE_ADAPTATION=True