import pandas as pd
from strava_api_calls_v2 import *
from strava_cfg import *

'''
File to export GPS coordinates for runs
TODO: This could likely be made a child class of process_strava_data
'''

class Strava_single_run_data(object):

    def __init__(self, raw_strava_df):
        self.raw_strava_df = raw_strava_df
        self.EDA_df = None
        self.trans_df = None
        self.processed_df = None
        self.add_feat_df = None

    def shift_latlng(self, df):
        df['prev_latlng'] = df['latlng'].shift(1)
        return df['prev_latlng'].fillna(df['latlng'])

    def shift_alt(self, df):
        df['prev_alt'] = df['altitude'].shift(1)
        return df['prev_alt'].fillna(df['altitude'])

    def calc_alt_delta(self, row):
        return row['altitude'] - row['prev_alt']

    def shift_dist(self, df):
        df['prev_dist'] = df['distance'].shift(1)
        return df['prev_dist'].fillna(0)

    def calc_dist_delta(self, row):
        return row['distance'] - row['prev_dist']

    def setup_input(self):
        '''
        Runs all the data prep functions. Output skips time 0 due to irregularities
        (e.g., distance > 0 at time = 0)
        :param input_df:
            Activity stream from Strava
        :return:
            dataframe with temp, time, cadence, distance, altitude, heartrate,
            and calculated pace using device reported distance
        '''
        features = ['temp', 'time','cadence', 'distance', 'altitude',
                    'heartrate', 'pace', 'lat', 'lng']
        self.EDA_df = self.raw_strava_df.copy()
        if not self.EDA_df['latlng'].apply(lambda x: type(x) == list).any():
        # latlng data imported as string vs. list in some instances
            self.EDA_df['latlng'] = self.EDA_df['latlng'].str.strip('[]').str.split(',')
            self.EDA_df['latlng'] = self.EDA_df['latlng'].apply(lambda x: [float(item) for item in x])

        self.EDA_df['pace'] = self.EDA_df['distance'] / self.EDA_df['time']
        self.EDA_df['pace'].fillna(0, inplace=True)
        self.EDA_df['lat'] = self.EDA_df['latlng'].apply(lambda x: x[0])
        self.EDA_df['lng'] = self.EDA_df['latlng'].apply(lambda x: x[1])
        self.EDA_df = self.EDA_df[features][1:]
        return self.EDA_df[1:]

    def extract_5s_increments(self, inc=5):
        output_df = pd.DataFrame()
        time_inc = [x * inc for x in range(1, (self.EDA_df['time'].max() // inc) + 1)]
        output_df['5s_intervals'] = time_inc
        output_df = output_df.merge(self.EDA_df, left_on='5s_intervals',
                                    right_on='time', how='left')
        self.trans_df = output_df

    def combine_t_inc_raw(self):
        self.extract_5s_increments()
        # filter all 5s increments not in raw data
        nan_df = self.trans_df[self.trans_df.isna().any(axis=1)]
        nan_df.drop('time', axis=1, inplace=True)
        nan_df.rename({'5s_intervals': 'time'}, axis=1, inplace=True)
        # Calculate 5s interval data based on averages of adjacent raw recordings
        for x in nan_df['time']:
            # grab raw data available immediately before and after missing 5s interval
            temp_df = self.EDA_df.iloc[(self.EDA_df['time'] - x).abs().argsort()[:2]]
            index = self.trans_df[self.trans_df['5s_intervals'] == x].index
            avg_cols = ['temp', 'cadence', 'heartrate', 'pace', 'altitude', 'lat', 'lng']
            wtd_avg_col = ['distance']
            for cols in avg_cols:
                # take simple mean to estimate metrics at missing 5s measurements
                self.trans_df.loc[index, cols] = temp_df[cols].mean()
            for cols in wtd_avg_col:
                # distance prorated rather than averaged
                temp_index1 = temp_df.index[0]
                temp_index2 = temp_df.index[1]
                t2 = temp_df.loc[temp_index2, 'time']
                feat2 = temp_df.loc[temp_index2, cols]
                self.trans_df.loc[index, cols] = feat2 * (x/t2)
        self.processed_df = self.trans_df.drop('time', axis=1)
        return self.processed_df.head(20)

    def alt_delta_forecast(self, alt_delta, period=6):
        '''
        Calculate
        :param alt_delta:
            Panda series containing altitude change in 5s increments
        :return:
            Cumulative altitude change for # periods in the future
        '''
        alt_forecast_list = []
        for index in range(len(alt_delta)):
            alt_forecast_list.append(alt_delta[index:index + period].sum())
        return alt_forecast_list

    def add_dist_alt_deltas(self):
        self.add_feat_df = self.processed_df
        self.add_feat_df['prev_alt'] = self.shift_alt(self.add_feat_df)
        self.add_feat_df['alt_delta'] = self.add_feat_df.apply(self.calc_alt_delta, axis=1)
        self.add_feat_df['prev_dist'] = self.shift_dist(self.add_feat_df)
        self.add_feat_df['dist_delta'] = self.add_feat_df.apply(self.calc_dist_delta, axis=1)
        self.add_feat_df['alt_forecast'] = self.alt_delta_forecast(self.add_feat_df['alt_delta'])
        return self.add_feat_df

if __name__ == '__main__':
    run_activity = int(input('Enter run id:'))
    client = StravaAPI(client_id, client_secret, refresh_token)
    sample_1 = client.get_route_stream(run_activity)
    latlng_ex = Strava_single_run_data(sample_1)
    latlng_ex.setup_input()
    latlng_ex.extract_5s_increments()
    latlng_ex.combine_t_inc_raw()
    latlng_ex.processed_df.to_csv(f'../raw_data/lat_lng_extract_{run_activity}.csv')