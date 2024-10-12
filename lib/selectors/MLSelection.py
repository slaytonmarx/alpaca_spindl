from lib.Selector import Selector
import random
import lib.tools.Scrivener as sc
import lib.tools.TimeKeeper as tk
import lib.tools.Broker as br
from lib.tools.Config import Config
import lib.tools.Tuner as Tuner
import importlib
import pandas as pd

import ray

class MLSelection(Selector):
    '''Selector which determines whether the given symbol is valid by way of machine learning'''
    
    def __init__(self, symbol:str, date:pd.Timestamp, strategy):
        super().__init__(symbol, date, strategy)
        
        self.ML = importlib.import_module('metadata.ml_configs.ML_'+self.strategy_name, package=None)
    
        #print('Initiating Search for',symbol)
        
        # Calculate lookback
        self.lookback = tk.give_n_days_ago(self.date, self.ML.DAY_LOOKBACK)

        # Adds ML dates to archive to avoid excessive data pulling
        api = br.paper_api()
        for date in tk.get_date_range((self.date - pd.DateOffset(days=self.lookback+1)), (self.date - pd.DateOffset(days=1))):
            sc.update_archive(self.symbol, date, api=api)
                                           
    def is_valid(self):
        '''Determines whether the symbol is worth trading today by running a regression search on it over the past n days (set in the ML config)'''
        score = self.regression_search()

        if len(score) > 0:
            self.sconf = self.populate_sconf(score.parameters)
            return score.score
        return False

    def populate_sconf(self, parameters:dict):
        '''Creates a new strategy config based off of the symbols template config, then populates it with the parameters given'''
        sconf = Config('s_'+self.strategy_name+'_'+self.symbol+'.json')
        for item in parameters.items():
            setattr(sconf, item[0], item[1])
        return sconf

    def generate_random_parameters(self):
        parameters = {}
        for parameter_name in self.ML.VALUE_RANGES:
            if 'EMA' in parameter_name: self.ema_handling(parameters, parameter_name)
            else: parameters[parameter_name] = self.r_in_range(self.ML.VALUE_RANGES[parameter_name])            
        return parameters
    
    def ema_handling(self, parameters:dict, ema_name:str):
        '''A dispicable hack to handle 3ema value dependencies'''
        match ema_name:
            case 'EMA1': parameters[ema_name] = self.r_in_range(self.ML.VALUE_RANGES[ema_name])
            case 'EMA2':
                ema2_start = parameters['EMA1'] + 1 if parameters['EMA1'] > self.ML.VALUE_RANGES['EMA2'][0] else self.ML.VALUE_RANGES['EMA2'][0]
                parameters[ema_name] = random.randint(ema2_start, self.ML.VALUE_RANGES['EMA2'][1])
            case 'EMA3':
                ema3_start = parameters['EMA2'] + 1 if parameters['EMA2'] > self.ML.VALUE_RANGES['EMA3'][0] else self.ML.VALUE_RANGES['EMA3'][0]
                parameters[ema_name] = random.randint(ema3_start, self.ML.VALUE_RANGES['EMA3'][1])

    def r_in_range(self, r:list):
        '''Returns a random number from the list, fully inclusive'''
        return random.randint(r[0], r[1])

    @ray.remote
    def run_experiment(self, parameters:list):
        '''Runs a tuning experiment on the given symbol'''
        sconf = self.populate_sconf(parameters)
        results = Tuner.tuning(s=(self.date - pd.DateOffset(days=self.lookback+1)), e=(self.date - pd.DateOffset(days=1)), strategy=self.strategy, allow_output=self.ML.SHOW_RUNS, sconfs={self.symbol: sconf}, symbols=[self.symbol])#allow_output=False,
        return parameters, results
    
    def score_function(self, profit:pd.Series):
        '''Returns the score for the set of days'''
        return (profit.sum() - profit[profit < 0].sum() * self.ML.LOSS_FACTOR).profit

    def generate_next(self, param_key:str, sign, parameters, steps, ranges):
        '''Returns the parameter modifier based on the associated step and parameter, ensuring
            that the result is within the range of the given param. We havea couple of relations
            we need to keep in mind. Firstly, the emas cannot be larger than their higher
            neighbor, and secondly, no value can be above the range set for them.
        '''
        initial = parameters[param_key]

        param_change = steps[param_key] * sign
        next_step = initial + param_change
        if next_step < ranges[param_key][0]: return ranges[param_key][0]
        elif next_step > ranges[param_key][1]: return ranges[param_key][1]
        
        # Ema modifier handling
        if 'EMA' in param_key:
            match param_key:
                case 'EMA1':
                    if next_step > parameters['EMA2']: return parameters['EMA2'] - 1
                case 'EMA2':
                    if next_step < parameters['EMA1']: return parameters['EMA1'] + 1
                    if next_step > parameters['EMA3']: return parameters['EMA3'] - 1
                case 'EMA3':
                    if next_step < parameters['EMA2']: return parameters['EMA2'] + 1
        return next_step

    def gradient_descent(self, params:dict, initial_score:int = -100000):
        '''Runs a gradient descent attempt on the given parameter set and returns the best score and parameters associated'''
        best_params, best_score = params.copy(), initial_score
        step_sizes = self.ML.STEP_SIZES.copy()

        for step_i in range(self.ML.DESCENT_STEPS):
            step_results, step_parameters = [], []

            for parameter in best_params:
                for sign in [1, -1]:
                    testing_params = best_params.copy()

                    # Different modifiers between ema and atr
                    next_value = self.generate_next(parameter, sign, best_params, step_sizes, self.ML.VALUE_RANGES)
                    testing_params[parameter] = next_value
                    step_parameters.append(testing_params)
            parameterized_runs = [self.run_experiment.remote(self, parameters) for parameters in step_parameters]
            step_results = pd.DataFrame([{'parameters': res[0], 'score': self.score_function(res[1])} for res in ray.get(parameterized_runs)])
            best_pair = step_results.sort_values('score').iloc[-1]

            if best_pair.score > best_score: best_params, best_score = best_pair.parameters, best_pair.score
            elif list(self.ML.STEP_SIZES.values())[0] == list(step_sizes.values())[0] and self.ML.ALLOW_HIGHRANGE_ADAPTATION:
                for step_name in step_sizes: step_sizes[step_name] *= 2; #print('No movement, attempting larger step size\nnew step size is', step_sizes)
            else: break#print("OK, we're done with ", best_params, best_score); break
        return best_params, best_score

    def regression_search(self):
        '''Runs a full regression search to determine the best possible parameters for the symbol, for the given time'''
        initial_parameters = [self.generate_random_parameters() for i in range(self.ML.INITIAL_SEED_COUNT)]

        # Evaluate Initial Seeds
        initial_runs = [self.run_experiment.remote(self, parameters) for parameters in initial_parameters]
        initial_results = pd.DataFrame([{'parameters': res[0], 'score': self.score_function(res[1])} for res in ray.get(initial_runs)]).sort_values('score').iloc[-self.ML.CONTENDER_COUNT:]
        if initial_results.iloc[-1].score <= 0: return []#print(self.symbol,' could not produce profit'); return []

        # Run Gradient Descent on Seeds
        descent_scores = []
        for parameters in initial_results.parameters:
            parameters, score = self.gradient_descent(parameters)
            descent_scores.append({'score':score, 'parameters':parameters})
        descent_scores = pd.DataFrame(descent_scores)
        best_score = descent_scores.sort_values('score').iloc[-1]
        if self.ML.SHOW_RUNS: print('Our parameters for',self.symbol,'on',self.date,'are',best_score.parameters)
        return best_score