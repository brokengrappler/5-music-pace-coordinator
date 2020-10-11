import requests
import base64
import datetime
import pandas as pd
import json
from urllib.parse import urlencode

import spotify_cfg
token_url = 'https://accounts.spotify.com/api/token'

class SpotifyAPI(object):
    '''
    List of functionalities that can be called:
    * get_resource(lookup_id, resource_type): look up track/album/artist detail based on Spotify id
    * search(query=None, search_type='artist'): general query, specify artist/album/playlist etc. search type
    * play(): start play on a given device
    * get_playlist(playlist_id): get list of tracks and track info on a playlist
    * get_audio_features(uri_list): get audio features for a list of uris.
    * add_song_queue(uri): add song to user's queue
    '''
    def __init__(self, client_id, client_secret, *args, **kwargs):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = spotify_cfg.refresh_token
        self.token_url = token_url
        self.access_token = None
        self.access_token_expires = datetime.datetime.now()
        self.access_token_did_expire = True

    def get_client_credentials(self):
        '''
        Returns a base64 encoded string
        '''
        client_id = self.client_id
        client_secret = self.client_secret
        if client_id == None or client_secret == None:
            raise Exception('You must set client_id and client_secret')
        client_creds = f'{client_id}:{client_secret}'
        client_creds_b64 = base64.b64encode(client_creds.encode())
        return client_creds_b64.decode()

    def get_token_headers(self):
        client_creds_b64 = self.get_client_credentials()
        return {
            'Authorization': f'Basic {client_creds_b64}'
        }

    def get_resource_header(self):
        access_token = self.get_access_token()
        header = {
            'Authorization': f'Bearer {access_token}'
        }
        return header

    def perform_auth(self):
        token_headers = self.get_token_headers()
        payload = {
            'refresh_token':self.refresh_token,
            'grant_type':'refresh_token'
        }
        r = requests.post(self.token_url, data=payload, headers=token_headers)
        if r.status_code not in range(200, 300):
            raise Exception('Could not authenticate client')
            # return False
        data = r.json()
        now = datetime.datetime.now()
        access_token = data['access_token']
        expires_in = data['expires_in']
        expires = now + datetime.timedelta(seconds=expires_in)
        self.access_token = access_token
        self.access_token_expires = expires
        self.access_token_did_expire = expires < now
        return True

    def get_access_token(self):
        token = self.access_token
        expires = self.access_token_expires
        now = datetime.datetime.now()
        if expires < now:
            self.perform_auth()
            return self.get_access_token()
        elif token is None:
            self.perform_auth()
            return self.get_access_token()
        return token

    def get_resource(self, lookup_id, resource_type='albums', version='v1'):
        endpoint = f'https://api.spotify.com/{version}/{resource_type}/{lookup_id}'
        headers = self.get_resource_header()
        r = requests.get(endpoint, headers=headers)
        if r.status_code not in range(200, 299):
            return {}
        return r.json()

    def get_album(self, _id):
        return self.get_resource(_id, resource_type='albums')

    def get_artist(self, _id):
        return self.get_resource(_id, resource_type='artists')

    def base_search(self, query_params):
        header = self.get_resource_header()
        endpoint = 'https://api.spotify.com/v1/search'
        lookup_url = f'{endpoint}?{query_params}'
        r = requests.get(lookup_url, headers=header)
        if r.status_code not in range(200, 300):
            return {}
        return r.json()

    def search(self, query=None, operator=None, operator_query=None, search_type='artist'):
        if query == None:
            raise Exception('Query required')
        if isinstance(query, dict):
            query = ' '.join([f'{k}:{v}' for k, v in query.items()])
        if operator != None and operator_query != None:
            if operator.lower() == 'or' or operator.lower() == 'not':
                operator = operator.upper()
                if isinstance(operator_query, str):
                    query = f'{query} {operator} {operator_query}'
        query_params = urlencode({'q': query, 'type': search_type.lower()})
        print(query_params)
        return self.base_search(query_params)

    def play(self, qtype='playlist', uri='3YgpDQqiu3hSEyRczMvJ9F'):
        # what goes in context uri?
        device = self.get_device_list()
        headers = self.get_resource_header()
        endpoint = f'https://api.spotify.com/v1/me/player/play?device_id={device}'
        query = f'spotify:{qtype}:{uri}'
        if qtype == 'track':
            body = {'uris':[query]}
        else:
            body = {'context_uri':query}
        print(body)
        r = requests.put(endpoint, headers=headers, data=json.dumps(body))

    def get_device_list(self, device_type='Computer'):
        headers = self.get_resource_header()
        endpoint = f'https://api.spotify.com/v1/me/player/devices'
        r = requests.get(endpoint, headers=headers).json()
        for device in r['devices']:
            if device['type'] == device_type:
                return device['id']
            else:
                continue
        return 'Select valid device'

    def get_playlist(self, playlist_id):
        headers = self.get_resource_header()
        endpoint = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        r = requests.get(endpoint, headers=headers)
        return r.json()

    def get_audio_features(self, uri_list):
        '''
        Get audio features of tracks (tempo) for songs from playlist
        :param uri_list:
            List of song uris (get_playlist_uris())
        :return:
            Pandas DF with track list and audio features
        '''
        # raw dictionary output from API request
        headers = self.get_resource_header()
        endpoint = f'https://api.spotify.com/v1/audio-features?ids='
        uri_cs = '%2C'.join(uri_list)
        r = requests.get(endpoint + uri_cs, headers=headers)
        edm_af = r.json()

        # Organize output into a pandas DF
        af_df = pd.DataFrame()
        for songs in edm_af['audio_features']:
            af_df = af_df.append(songs, ignore_index=True)
        return af_df

    def add_song_queue(self, uri):
        headers = self.get_resource_header()
        endpoint = f'https://api.spotify.com/v1/me/player/queue?uri={uri}'
        r = requests.post(endpoint, headers=headers)
        return r

    def next_song(self):
        headers = self.get_resource_header()
        endpoint = 'https://api.spotify.com/v1/me/player/next'
        r = requests.post(endpoint, headers=headers)
        return r