import pandas as pd
import numpy as np
import random
from scipy import stats

from strava_api_calls_v2 import *
from process_strava_data import *

class fbp_data_prep(StravaAPI):
    '''
    Instance of StravaAPI class. StravaAPI has multiple functions for querying data.
    '''

    def __init__(self, client_id, client_secret, refresh_token, run_id, *args, **kwargs):
        super().__init__(client_id, client_secret, refresh_token)
        # run_list contains all run data; may not be needed
        self.run_list = self.get_run_list()
        self.activity_list = super().get_activity_list()
        self.run_id = run_id

    def get_run_list(self):
        '''
        DF contain details of prior runs (i.e., get_route_stream)
        :return:
            dataframe
        '''
        updated_list = self.activity_list['id']
        return list(updated_list)

    def train_test_split_runs(self, train_size=.8, random_state=444):
        '''
        Reserves a set of runs from run activity list to be split between train and test.
        TODO: This isn't used yet but will be once I move to a sequence to sequence model.
        :param train_size:
            float: desired train size percentage
        :param random_state:
        :return:
        train (list): list of indices for runs that are in the train set
        test (list): list of indices for runs that are in the test set
        '''
        # need list of run from run_list
        num_runs = len(self.run_list)
        train_len = int(num_runs*train_size)
        random.seed(random_state)
        train = random.sample(self.run_list, k=train_len)
        test = [x for x in self.run_list if x not in train]
        return train, test

    def prep_raw_run_data(self, random_state=444):
        '''
        Selects a run from the train list and request the route stream info from Strava
        :return:
        sample_run (int): Strava run id selected for run_info
        run_info (dataframe): runstream data from Strava in dataframe format
        '''
        # Select one "random" run for now; if we do a multi-time series,
        # need to run this on data for all runs
        train_list = self.train_test_split_runs()[0]
        random.seed(random_state)
        if self.run_id:
            sample_run = self.run_id
        else:
            sample_run = random.choice(train_list)
        run_info = super().get_route_stream(sample_run)
        #run_info.to_csv(f'../raw_data/raw_run_data{sample_run}.csv')
        # filter extreme outliers ( |z| > 10)
        run_info = run_info[np.abs(stats.zscore(run_info['cadence'])) < 10]
        return sample_run, run_info

def process_data(chosen_run_id):
    '''
    Process data and attach run date
    :return:
        run_id (int): Strava run_id; if none selected, data for run 3247665259 returned
        run_date(datetime n64): starting date time to be used per Facebook Prophet requirement
        process_data.add_feat_df: Strava data put in form to report data at 5s intervals
    '''
    # Processes data into 5s intervals
    # Calculates distance and altitude changes
    # for test_class, input a run_id argument if we want to see a specific run_id
    test_class = fbp_data_prep(client_id, client_secret, refresh_token, chosen_run_id)
    run_id, raw_run_df = test_class.prep_raw_run_data()
    process_data = Strava_single_run_data(raw_run_df)
    process_data.setup_input()
    process_data.combine_t_inc_raw()
    process_data.add_dist_alt_deltas()

    # 1) Find run date/time; 2) remove time zone info
    run_date = test_class.activity_list[test_class.activity_list['id'] == run_id]['start_date']
    return run_id, run_date, process_data.add_feat_df

if __name__ == '__main__':
    print(process_data()[0])