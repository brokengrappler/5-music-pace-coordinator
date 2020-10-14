

# Description

Phase I project to simulate automatic music selection to aid effort and pace through future segments of a planned run. Interacts with Strava and Spotify API to get data and control music on user's device.

run_playlist_presentation.py is a script that:

1) Asks for a specific Activity ID from Strava
2) Predicts pace and cadence for the next 30 second interval
3) Selects music at a specified BPM to suggest steps per minute metrics to keep consistent with targeted pace (currently default to historical avg based on Strava data)

# API Codes Needed for Spotify and Strava
- client_id
- client_secret 
- refresh_token 

For Spotify, your code will specifically need the following grant access: user-modify-playback-state, playlist-modify-private

Create files called 'strava_cfg.py' and 'spotify_cfg.py' each containing the codes

e.g.:
```
client_id = 'ENTER YOUR ID'
client_secret = 'ENTER YOUR CODE'
refresh_token = 'ENTER CODE'
```

# Dependencies
tqdm==4.48.2  
urllib3==1.25.9  
requests==2.24.0  
pandas==1.0.5  
numpy==1.18.5  
scipy==1.5.0  
fbprophet==0.7.1  

# Files

#### Primary

- **run_playlist_presentation.py**: Primary script to run and demonstrate function. Depends on all python scripts below.

#### Supporting

- **strava_api_calls_v2.py:** Class whose primary function is to pull data from Strava
- **spotify_client_PC.py**: Class used to interact with Spotify API
- **process_strava_data.py:** Class that reformats data to be in 5s intervals plus feature engineering
- **prep_data_fbp.py**: Subclass of strava_api_calls_v2. Pulls data and uses process_strava_data to process the data
- **lat_lng_extract.py**: Extracts GPS coordinates from Strava run to be used as input
- **fb_forecast_cadence.py**: Script creates FB Prophet predictions on run cadence
- **fb_forecast_pace.py**: Script creates FB Prophet predictions on run pace

# Sample Dashboard Snapshot

![](/final_video/dashboard.png)

# Next Phase(s)
- incorporate rest days and heart rate predictions
- an interface for entering/uploading GPS coordinates
- expand music capabilities (select genre, fade-in/out music type)
- recursively improve: Unsupervised learning to observe how different audio features affect a runner's pace
- Have a setting to adjust the music not for just maintaining speed, but for maintaining a certain heart rate zone
- incorporate biking?

Issues
- Can't figure out how Garmin is calculating distance. Distances calculated using GPX and geopy do not reconcile with Strava distances. Not terribly off but can get worse as distance increases. 

