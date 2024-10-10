import lib.tools.TimeKeeper as tk
import pandas as pd
import glob
import pytz
import os

ENABLE_LOGGING = True

def log(api, date:pd.DatetimeIndex, symbol:str, header:str, msg:dict):
    '''Writes the log to the appropriate log file'''
    if not ENABLE_LOGGING: return
    
    directory = parse_directory(api, date)
    if not os.path.isdir(directory): os.mkdir(directory)
    header = 'BR_'+header if api else 'TR_'+header
    logfile = parse_logfile(directory, header, symbol)

    # Parse Log Line
    time = str(date.hour).rjust(2,'0')+':'+str(date.minute).rjust(2,'0')+':'+str(date.second).rjust(2,'0')
    line = time+'\t'+'\t'.join([str(val) for val in msg.values()])
    
    # Create Symbol File
    if os.stat(logfile).st_size == 0:
        with open(logfile, 'a') as f:
            f.write('index\t'+'\t'.join(list(msg.keys())))
    # with open(logfile, 'r') as f:
    #     if f.readlines()[-1].split('\t')[0] == time: return
    with open(logfile, 'a') as f:
        f.write('\n'+line)

def clear_logs(api, date:pd.DatetimeIndex, symbol:str):
    '''Clears the log of the given date'''
    directory = parse_directory(api, date)
    logs_to_clear = glob.glob(directory+symbol+'*')
    for log in logs_to_clear:
        with open(log,'w') as f: f.write('')

def parse_directory(api, date:pd.DatetimeIndex):
    '''Returns the date directory of the log file'''
    root = 'spindl/logs/'
    base = root+'brokerage/' if api else root+'training/'
    directory = base+str(date.year)+'-'+str(date.month).rjust(2,'0')+'-'+str(date.day).rjust(2,'0')+'-'+date.day_name()[:3]+'/'
    return directory

def parse_logfile(directory, header, symbol):
    '''Returns the logfile name for the given information'''
    logfile = directory+symbol+'_'+header+'.tsv'
    if not os.path.isfile(logfile): open(logfile, 'a').close()
    return logfile

def reflection(date:pd.DatetimeIndex, symbol:str, header:str):
    '''Goes through the logs for the given day in live and training and compares them, prints any differences'''
    brokerage_dir, training_dir = parse_directory(True, date), parse_directory(None, date)
    if not os.path.isdir(brokerage_dir) or not os.path.isdir(training_dir): raise Exception('One of both log directories are missing')
    brokerage_file, training_file = parse_logfile(brokerage_dir, header, symbol), parse_logfile(training_dir, header, symbol)
    if not os.path.isfile(brokerage_file) or not os.path.isfile(training_file): raise Exception('One of both log files are missing')
    
    with open(brokerage_file,'r') as f:
        broker_logs = {line.split('|')[0] : line.split('|')[1].strip() for line in f.readlines()}
    with open(training_file,'r') as f:
        training_logs = {line.split('|')[0] : line.split('|')[1].strip() for line in f.readlines()}

    diff = []
    compare_logs(broker_logs, training_logs, diff)
    compare_logs(training_logs, broker_logs, diff)
    
    for d in diff: print(d)
    if not diff: return True
    return False

def compare_logs(source_log:dict, target_log:dict, diff:list):
    for key in source_log:
        if not key in target_log: diff.append('\t'+key+' Not in Training Logs')
        elif source_log[key] != target_log[key]: diff.append('\t'+key+' is '+source_log[key]+' in source but '+target_log[key]+' in target')

def get_log(symbol:str, date:pd.DatetimeIndex, stream:str = 'training', log_type:str = 'OPS'):
    '''Returns the log, in dataframe form, for the given symbol on the given date for the given stream, assuming training as default'''
    log_path = os.path.join('logs',stream,date.strftime("%Y-%m-%d-%a"),symbol.upper()+'_'+stream[:2].upper()+'_'+log_type.upper()+'.tsv')
    if not os.path.isfile(log_path): log_path = '../'+log_path
    log = pd.read_csv(log_path, delimiter='\t').set_index('index')
    log.index = pd.to_datetime(f'{date.year}-'+str(date.month).rjust(2,'0')+f'-{date.day}T'+log.index, format='ISO8601').tz_localize(pytz.timezone('America/New_York'))
    return log