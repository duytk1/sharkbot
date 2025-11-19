import asyncio
import threading
import sqlite3
import logging

from sharkai import SharkAI
from sharkbot import start_bot
from chat_overlay_server import app as chat_overlay_app
import time
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("App")


def run_bot():
    """Run the Twitch/YouTube bot."""
    try:
        asyncio.run(start_bot())
    except Exception as e:
        LOGGER.error(f"Bot error: {e}")


def run_chat_overlay():
    """Run the chat overlay web server."""
    try:
        LOGGER.info("Starting chat overlay server on http://localhost:5000")
        chat_overlay_app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        LOGGER.error(f"Chat overlay server error: {e}")


def run_spotify_overlay():
    """Run the Spotify overlay (writes to spotify_now_playing.txt)."""
    try:
        LOGGER.info("Starting Spotify overlay")
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
            client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.environ.get("SPOTIFY_CALLBACK_URI"),
            scope="user-read-playback-state"
        ))
        
        while True:
            try:
                current = sp.current_playback()
                if current and current.get("is_playing") and current.get("item"):
                    name = current["item"]["name"]
                    artist = current["item"]["artists"][0]["name"]
                    song = f"♫ {name} - {artist}"
                else:
                    song = "No music playing"
            except Exception as e:
                LOGGER.error(f"Error fetching Spotify song: {e}")
                song = "Error fetching song info"
            
            try:
                with open("spotify_now_playing.txt", "w", encoding="utf-8") as f:
                    f.write(song)
            except Exception as e:
                LOGGER.error(f"Error writing Spotify file: {e}")
            time.sleep(5)
    except Exception as e:
        LOGGER.error(f"Spotify overlay error: {e}")


if __name__ == "__main__":
    # Clear messages database on startup
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages;")
        conn.commit()
        cursor.close()
        conn.close()
        LOGGER.info("Cleared messages database")
    except Exception as e:
        LOGGER.warning(f"Could not clear messages database: {e}")
    
    # Start bot in background thread
    LOGGER.info("Starting bot...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start chat overlay server in background thread
    LOGGER.info("Starting chat overlay server...")
    chat_overlay_thread = threading.Thread(target=run_chat_overlay, daemon=True)
    chat_overlay_thread.start()
    
    # Start Spotify overlay in background thread
    LOGGER.info("Starting Spotify overlay...")
    spotify_thread = threading.Thread(target=run_spotify_overlay, daemon=True)
    spotify_thread.start()
    
    LOGGER.info("=" * 60)
    LOGGER.info("All services started!")
    LOGGER.info("=" * 60)
    LOGGER.info("Bot: Running in background")
    LOGGER.info("Chat Overlay: http://localhost:5000")
    LOGGER.info("Spotify Overlay: Writing to spotify_now_playing.txt")
    LOGGER.info("=" * 60)
    LOGGER.info("Press Ctrl+C to stop all services")
    LOGGER.info("=" * 60)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("\nShutting down all services...")
        # Daemon threads will be killed automatically
