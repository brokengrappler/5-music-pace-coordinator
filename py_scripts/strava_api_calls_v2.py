import requests
import pandas as pd
import datetime
import time
import urllib3
from tqdm import tqdm
from strava_cfg import *

token_url = 'https://www.strava.com/api/v3/oauth/token'

class StravaAPI(object):
    '''
    Class used to communicate with Strava API. Functions include:
        * getting activity list
        * specific run data
    TODO: Create function to get access token for other users. Will entail creating a web module that gets the token after receiving approval from user
    '''
    def __init__(self, client_id, client_secret, refresh_token, *args, **kwargs):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token, self.token_expire_time = self.get_access_token()
        self.activity_list = self.get_activity_list()
        self.error_log = None

    def get_access_token(self):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
            'f': 'json'
        }
        # auth_url[0] is token refresh url; auth_url[1] is initial token
        auth_url = [
            'https://www.strava.com/api/v3/oauth/token',
            f'https://www.strava.com/oauth/authorize?client_id={self.client_id}&redirect_uri=http://localhost&response_type=code&scope=activity:read_all'
        ]
        if self.refresh_token:
            res = requests.post(auth_url[0], data=payload, verify=False).json()
            access_token = res['access_token']
            token_expire_time = datetime.datetime.now() + datetime.timedelta(seconds=res['expires_in'])
        else:
            # fill in function for extracting other users' access token
            res = requests.get(auth_url[1])
            res_url = res.url
            # extract access token from url;
        return access_token, token_expire_time

    def get_response(self, url):
        if datetime.datetime.now() > self.token_expire_time:
            self.get_access_token()
        if self.access_token:
            headers = {'Authorization': 'Bearer ' + self.access_token,
                       "Accept": "application/json",
                       "Content-Type": "application/json"
                       }
            response = requests.request(
                "GET",
                url,
                headers=headers
            )
            data = response.json()
        else:
            print('Must get access token first')
        return data

    def process_activity_list(self, df):
        output_df = df.drop(['location_city', 'location_state', 'location_country'], axis=1).copy()
        output_df['start_date'] = pd.to_datetime(output_df['start_date'])
        output_df['start_date_local'] = pd.to_datetime(output_df['start_date_local'])
        return output_df

    def get_activity_list(self):
        '''
        Call API for list of activities and filter 'Run' only
        '''
        activity = ['Run']
        endpoint = "https://www.strava.com/api/v3/athlete/activities?per_page=200"
        list_activities_output = self.get_response(endpoint)
        list_df = self.process_activity_list(pd.DataFrame(list_activities_output))
        activity_list = list_df[list_df['type'].isin(activity)]
        return activity_list

    # THIS METHOD BROKE AT SOME POINT; PROBABLY NEED TO FIX ENDPOINT URL
    # def get_heart_zones(self):
    #     endpoint = "https://www.strava.com/api/v3/activities/3942323714/zones"
    #     hz_output = self.get_response(endpoint)
    #     return hz_output

    def get_route_stream(self, run_id):
        df = pd.DataFrame()
        url = "https://www.strava.com/api/v3/activities/" +str(run_id)+ "/streams?keys=time,distance,latlng,altitude,velocity_smooth,heartrate,cadence,temp,grade_smooth&key_by_type=true"
        rt_stream_output = self.get_response(url)
        for k, v in rt_stream_output.items():
            df[k] = v['data']
        return df

    def extract_run_data(self):
        '''
        Creates a dataframe that aggregates data for all runs
        :return:
            (dataframe): includes all features from get_route_stream function
        '''
        df = pd.DataFrame()
        for acts in tqdm(self.activity_list['id']):
            try:
                rt_df = self.get_route_stream(acts)
            except:
                self.error_log.append(acts)
            else:
                rt_df.insert(0, 'activity_id', acts)
                df = pd.concat([df, rt_df])
                time.sleep(10)
        return df