import pandas as pd
import random
import time

from spotify_client_PC import *
from process_prophet_output_pace import analyze_run_for_music
import spotify_cfg

'''
This script was created for demo purposes only. I used it as a tool for presenting my final project at Metis
'''


def select_playlist(query='EDM 150 bpm'):
    '''
    Ping Spotify to get a playlist. At current phase, a specific playlist is manually chosen.
    :param query:
        search words as string
    :return:
        Row data in data frame for selected playlist. Use as argument in get_playlist_uris
    '''
    edm_music_query = spc.search(query, search_type='playlist')
    edm_query_df = pd.DataFrame(edm_music_query['playlists']['items'])
    clean_df = process_df(edm_query_df)
    # Manually selecting a specific playlist
    edm_pl = edm_query_df.loc[2, 'name']
    selected_pl = clean_df[edm_query_df['name'] == edm_pl]
    return selected_pl

def process_df(df):
    '''
    Reorganizes json format data returned from Spotify to data frame
    :param df:
        Data frame of raw data returned from Spotify query
    :return:
        Processed data frame with select features
    '''
    filter_df = df.drop(['collaborative', 'description', 'external_urls','images',
                         'owner', 'primary_color', 'public'], axis=1).copy()
    for cols in filter_df.columns:
        filter_df[cols] = filter_df[cols].apply(lambda x: x.values() if isinstance(x, dict) else x)
    return filter_df

def get_playlist_uris(selected_pl):
    '''
    Communicates with the Spotify API to get the list of song URIs in a playlist
    :param selected_pl:
        (string): uri code for a playlist in Spotify
    :return:
        (list): list of codified strings associated with songs
    '''
    playlist_df = pd.DataFrame()
    # MANUALLY SELECTING PLAYLIST FROM SEARCH; revisit to improve
    # Specific EDM playlist selected here; replace with selected_pl parameter in future iteration
    pl_songs = spc.get_playlist('3YgpDQqiu3hSEyRczMvJ9F')
    for x in pl_songs['items']:
        playlist_df = playlist_df.append(x['track'], ignore_index=True)
    uri_list = list(playlist_df['uri'].apply(lambda x: x.split(':')[2]))
    return uri_list

def process_audio_features(edm_af):
    '''
    Bins songs into 3 categories based on tempo
    :param edm_af:
        (dataframe) Pandas DF of results returned when Spotify pinged for song audio features
    :return:
        (dataframe) Pandas DF with column containing slower/faster song info
    '''
    edm_af['tempo_bin'] = pd.qcut(edm_af['tempo'], 3, labels=['slower', 'none', 'faster'])
    edm_af['duration_ms'] = edm_af['duration_ms'] / 1000
    return edm_af

def next_track_idx(edm_af, current_state):
    '''
    Selects the next song at the appropriate speed within the playlist
    :param edm_af:
        (dataframe) dataframe of audio features plus bin info based on tempo
    :param current_state:
        (string) label for music speed (slower/none/faster)
    :return:
        (int) index of song to be selected in the playlist
    '''
    choice = edm_af[edm_af['tempo_bin'] == current_state].index
    song_idx = random.choice(list(choice))
    return song_idx

def initiate_playback(total_df):
    '''
    Selects the first song
    :param total_df:
        (dataframe) Output dataframe from the time-series model
    :return:
        music_len (int): duartion of song in milliseconds
        init_state (string): initial speed of song selected (slower/none/faster)
    '''
    init_state = total_df.loc[0, 'sng_speed_change']
    init_song_idx = next_track_idx(edm_af, init_state)
    init_song_uri = edm_af.loc[init_song_idx, 'uri'].split(':')[2]
    music_len = edm_af.loc[init_song_idx, 'duration_ms']
    print(f"tempo:{edm_af.loc[init_song_idx, 'tempo']}")
    spc.play(qtype='track', uri=init_song_uri)
    return music_len, init_state

if __name__ == '__main__':

    spc = SpotifyAPI(spotify_cfg.client_id, spotify_cfg.client_secret)

    # Get audio features from playlist songs
    selected_pl = select_playlist(query='EDM 150 bpm')
    uri_list = get_playlist_uris(selected_pl)
    edm_af = spc.get_audio_features(uri_list)
    edm_proc_af = process_audio_features(edm_af)
    total_df, run_id = analyze_run_for_music()
    start_time=int(input('Enter Time Interval:'))
    # initiate playback and keep track of music length
    # Note adjustment to music length for presentation due to changing starting point
    global_music_len, current_state = initiate_playback(total_df)
    global_music_len += 180+start_time*30
    for times in range(start_time, total_df.shape[0]):  # len 90
        print(times)
        proj_tempo = total_df.loc[times, 'sng_speed_change']
        # if the tempo needs to be changed
        if proj_tempo != current_state:
            current_state = proj_tempo
            choice = edm_af[edm_af['tempo_bin'] == current_state].index
            song_idx = next_track_idx(edm_af, current_state)
            song_uri = edm_af.loc[song_idx, 'uri']
            print(f"tempo: {edm_af.loc[song_idx, 'tempo']}")
            spc.add_song_queue(song_uri)
            spc.next_song()
        # song will end in next time interval; queue new
        if (global_music_len - total_df.loc[times, 'ds']) < 30:
            choice = edm_af[edm_af['tempo_bin'] == current_state].index
            song_idx = next_track_idx(edm_af, current_state)
            song_uri = edm_af.loc[song_idx, 'uri']
            spc.add_song_queue(song_uri)
            print(edm_af.loc[song_idx, 'tempo'])
            global_music_len += edm_af.loc[song_idx, 'duration_ms']
            print(f'song time remaining from new add:{global_music_len}')
        # Emulating time sleep 30 seconds
        time.sleep(30)
