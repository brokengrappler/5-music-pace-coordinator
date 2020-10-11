import pandas as pd
import numpy as np
from fbprophet import Prophet
import os
from tqdm import tqdm

from prep_data_FBP import process_data

''' Script to run predictions on cadence for a run

TODO: 
1) Aggregate functions below into a class to get rid of global variables
2) Create parent class to be shared with pace predictor
'''

x_exogenous = ['temp', 'distance', 'altitude', 'alt_delta', 'alt_forecast']

class suppress_stdout_stderr(object):
    '''
    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).

    '''
    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close the null files
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])

def create_fbp_df(chosen_run_id):
    '''
    Based on Strava run id, put together a dataframe in the appropriate format to be used in Facebook Prophet
    :param chosen_run_id:
        (int): Strava run id for run to be analyzed
    :return:
        (dataframe): time, cadence, 'temp', 'distance', 'altitude', 'alt_delta', 'alt_forecast'
    '''
    run_id, run_date, proc_data_df = process_data(chosen_run_id)
    print(f'Predicting pace for run: {run_id}')
    # Split data into time and exogenous vars
    x_time = ['5s_intervals', 'cadence']
    run_time = proc_data_df[x_time]
    run_time.rename({'5s_intervals': 'ds', 'cadence': 'y'}, axis=1, inplace=True)
    samp_run_exo = proc_data_df[x_exogenous]
    # FB Prophet only takes time as datetime64 with no time zone
    run_time['ds'] = (np.array(run_date) + run_time['ds'].astype('timedelta64[s]')).dt.tz_localize(None)
    exo_df = pd.DataFrame(samp_run_exo, index=samp_run_exo.index, columns=samp_run_exo.columns)
    fbp_df = run_time.join(exo_df)
    return fbp_df

def create_prophet_with_exo(feats):
    '''
    Instance facebook prophet model
    :param feats:
        (list):
    :return:
        Facebook Prophet model
    '''
    model = Prophet(interval_width=.95)
    for feat in feats:
        model.add_regressor(feat)
    return model

def fit_fbp_model(chosen_run_id, train_period = 36):
    # If train period is changed, value in process_prophete_output;analyze_music() function needs
    # to be revised as well. Need to link the values
    '''
    Fits and predicts as run progresses
    :param train_period:
        (int): number of initial training periods (each period being 5 seconds)
    :return:
        pace_pred_dict(dict): keys are 30 second time intervals and values are avg cadence for the corresponding period
        fbp_df (dataframe): Entire dataframe with all predictions for each 5s interval
    '''
    pace_pred_dict = {}
    fbp_df = create_fbp_df(chosen_run_id)
    # 5s per period (36 * 5 = 180 or 3 min of training)
    forecast_period = 6
    iters = (fbp_df.shape[0] - train_period) // forecast_period
    for periods in tqdm(range(iters)):
        m = create_prophet_with_exo(x_exogenous)
        running_fc = train_period + periods * forecast_period
        with suppress_stdout_stderr():
            m.fit(fbp_df.iloc[:running_fc])
        pred_frame = m.make_future_dataframe(periods=forecast_period, freq='5s')
        future_exog = fbp_df.loc[:, x_exogenous].reset_index()
        future_exog.drop('index', axis=1, inplace=True)
        pred_frame = pred_frame.join(future_exog)
        pred_pace = m.predict(pred_frame)
        # Record prediction at forecast points
        pred_time = pred_pace.iloc[-forecast_period,0]
        pace_pred_dict[pred_time] = pred_pace['yhat'][-forecast_period:].mean()
    return pace_pred_dict, fbp_df

def actual_vs_predict(chosen_run_id=None):
    '''
    (temp) Creates pickle files of prediction results. This can be deprecated once analysis is complete.
    :param chosen_run_id:
        (int): Selected Strava run id. If none provided, the default is selected
    :return:
        None: only pickle files saved
    '''
    temp_dict, fbp_df = fit_fbp_model(chosen_run_id)
    result_df = pd.DataFrame.from_dict(temp_dict, orient='index').reset_index()
    fbp_df.to_pickle('../pkls/result_fbp.pkl')
    result_df.rename({'index':'ds', 0:'yhat'}, axis=1, inplace=True)
    result_df = result_df.merge(fbp_df, on='ds')
    if chosen_run_id:
        result_df.to_pickle(f'../pkls/cadence_df_{chosen_run_id}.pkl')
    else:
        result_df.to_pickle('../pkls/cadence_df(train0).pkl')

if __name__ == "__main__":
    run_id = int(input('Enter run id:'))
    actual_vs_predict(run_id)
    # fit_fbp_model()
    # print(create_fbp_df().head(20))