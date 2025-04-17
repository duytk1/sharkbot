import os
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
    client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.environ.get("SPOTIFY_CALLBACK_URI"),
    scope="user-read-playback-state"
))

def get_current_song():
    try:
        current = sp.current_playback()
        if current and current.get("is_playing") and current.get("item"):
            name = current["item"]["name"]
            artist = current["item"]["artists"][0]["name"]
            return f"♫ {name} - {artist}"
        else:
            return "No music playing"
    except Exception as e:
        logging.error(f"Error while fetching current song: {e}")
        return "Error fetching song info"

while True:
    song = get_current_song()
    try:
        with open("spotify_now_playing.txt", "w", encoding="utf-8") as f:
            f.write(song)
    except Exception as e:
        logging.error(f"Error writing to file: {e}")
    time.sleep(5)
