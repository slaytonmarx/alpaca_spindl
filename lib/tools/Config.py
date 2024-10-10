import sys; sys.path.append('../../..'); sys.path.append('../..')
import subprocess
from os import path as p
import json

class Config:
    '''Class for the storage, reading, and writing of important variables necessary for runs'''

    def __init__(self, filename:str = 'base.json'):
        '''Reads the filename given and converts the values in the json into local variables'''
        self.filename = filename
        self.jdict = self.read_config(filename)
        
        for key in self.jdict: setattr(self, key, self.jdict[key])
        

    def read_config(self, filename:str):
        '''Reads the given config'''
        filename = self.format_filename(filename)
        if not p.isfile(filename): return {}
        with open(filename, 'r') as f: return json.load(f)
        
    def write_config(self, filename:str = None):
        '''Writes the config to the filename, or to itself, keeping the previous version as a backup if no filename is given'''
        if not filename: filename = self.filename
        if self.read_config(filename) == self.__dict__: return

        filename = self.format_filename(filename)

        if p.isfile(filename): subprocess.run('cp '+filename+' '+filename+'.bkp', shell=True)
        with open(filename, 'w') as f: json.dump(self.__dict__, f, indent = 6)

    def format_filename(self, filename:str):
        '''Formats the filename to the configs directory if it's being hard to find'''
        root_path = './metadata/trade_configs' if p.isdir('./metadata/trade_configs') else '../metadata/trade_configs'
        if '.json' not in filename: filename = filename+'.json'
        return p.join(root_path, filename)
    
    def __str__(self):
        '''Converts the config to be displayed as a string'''
        output = ''
        for l in dir(self):
            if not "__" in l: output += f'{l}: {getattr(self, l)}; '
        return output