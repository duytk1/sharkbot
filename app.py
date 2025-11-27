import asyncio
import threading
import sqlite3
import logging

from sharkai import SharkAI
from sharkbot import start_bot
import time
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from flask import Flask, render_template_string, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv()

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("App")

# Flask app setup
app = Flask(__name__)
CORS(app)
SQL_DB_PATH = os.environ.get("SQL_CONNECT", "messages.db")


def run_bot():
    """Run the Twitch/YouTube bot."""
    try:
        asyncio.run(start_bot())
    except Exception as e:
        LOGGER.error(f"Bot error: {e}")


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


# Flask routes
@app.route('/')
def index():
    """Redirect to chat overlay."""
    return send_from_directory('.', 'chat_overlay.html')


@app.route('/chat_overlay.html')
def chat_overlay():
    """Serve the chat overlay HTML."""
    return send_from_directory('.', 'chat_overlay.html')


@app.route('/links')
def links_manager():
    """Serve the links manager HTML."""
    return send_from_directory('.', 'links_manager.html')


@app.route('/api/chat')
def get_chat_messages():
    """Get recent chat messages for the overlay."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        
        # Ensure messages table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user TEXT NOT NULL,
                message TEXT NOT NULL,
                platform TEXT DEFAULT 'twitch',
                timestamp REAL DEFAULT (julianday('now'))
            )
        ''')
        
        # Get recent messages (last 50, ordered by most recent)
        cursor.execute('''
            SELECT from_user, message, platform, timestamp
            FROM messages
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            messages.append({
                'user': row[0],
                'message': row[1],
                'platform': row[2] if row[2] else 'twitch',
                'timestamp': row[3] if row[3] else None
            })
        
        conn.close()
        
        # Reverse to show oldest first (for overlay display)
        messages.reverse()
        
        return jsonify({'messages': messages})
    except Exception as e:
        LOGGER.error(f"Error fetching chat messages: {e}")
        return jsonify({'error': str(e), 'messages': []}), 500


@app.route('/api/links', methods=['GET'])
def get_links():
    """Get all links from database."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        
        # Ensure links table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        cursor.execute("SELECT key, value FROM links")
        rows = cursor.fetchall()
        links = {row[0]: row[1] for row in rows}
        conn.close()
        
        return jsonify(links)
    except Exception as e:
        LOGGER.error(f"Error fetching links: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/links', methods=['POST'])
def save_links():
    """Save links to database."""
    try:
        data = request.json
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        
        # Ensure links table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        for key, value in data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO links (key, value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        LOGGER.error(f"Error saving links: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/tts')
def get_tts_info():
    """Get TTS file info (timestamp to detect new files)."""
    import os
    from datetime import datetime
    
    TTS_FILE = 'tts.mp3'
    
    try:
        if os.path.exists(TTS_FILE):
            # Get file modification time
            mtime = os.path.getmtime(TTS_FILE)
            file_size = os.path.getsize(TTS_FILE)
            
            return jsonify({
                'exists': True,
                'timestamp': mtime,
                'size': file_size,
                'url': '/api/tts/audio'
            })
        else:
            return jsonify({
                'exists': False,
                'timestamp': None,
                'size': 0,
                'url': None
            })
    except Exception as e:
        LOGGER.error(f"Error getting TTS info: {e}")
        return jsonify({'error': str(e), 'exists': False}), 500


@app.route('/api/tts/audio')
def serve_tts_audio():
    """Serve the TTS audio file."""
    from flask import send_file
    import os
    
    TTS_FILE = 'tts.mp3'
    
    if os.path.exists(TTS_FILE):
        return send_file(TTS_FILE, mimetype='audio/mpeg')
    else:
        return jsonify({'error': 'TTS file not found'}), 404


@app.route('/api/streamer')
def get_streamer_name():
    """Get the streamer name for 7TV emote fetching."""
    streamer_name = os.environ.get("STREAMER_NAME", "sharko51")
    return jsonify({'streamer_name': streamer_name})


@app.route('/api/7tv/emotes')
def get_7tv_emotes():
    """Get 7TV emotes for the streamer."""
    import requests
    import json
    
    streamer_name = os.environ.get("STREAMER_NAME", "sharko51")
    
    try:
        emotes = {}
        
        # First, get user from 7TV
        LOGGER.info(f"Fetching 7TV user data for: {streamer_name}")
        user_response = requests.get(
            f'https://7tv.io/v3/users/twitch/{streamer_name}',
            timeout=10
        )
        
        if user_response.status_code != 200:
            LOGGER.warning(f"7TV user API returned status {user_response.status_code}: {user_response.text}")
        else:
            user_data = user_response.json()
            LOGGER.debug(f"7TV user data: {json.dumps(user_data, indent=2)[:500]}")
            
            # Get emote set ID - 7TV API v3 structure can vary
            emote_set_id = None
            if 'emote_set' in user_data:
                emote_set_obj = user_data['emote_set']
                if isinstance(emote_set_obj, dict):
                    emote_set_id = emote_set_obj.get('id')
                elif isinstance(emote_set_obj, str):
                    emote_set_id = emote_set_obj
            elif 'emote_sets' in user_data:
                emote_sets = user_data['emote_sets']
                if isinstance(emote_sets, list) and len(emote_sets) > 0:
                    # First item might be a string ID or an object
                    first_set = emote_sets[0]
                    if isinstance(first_set, str):
                        emote_set_id = first_set
                    elif isinstance(first_set, dict):
                        emote_set_id = first_set.get('id')
                elif isinstance(emote_sets, dict):
                    emote_set_id = emote_sets.get('id')
            
            # Also try 'id' directly on user_data (some API versions)
            if not emote_set_id and 'id' in user_data:
                emote_set_id = user_data.get('id')
            
            if emote_set_id:
                LOGGER.info(f"Fetching 7TV emote set: {emote_set_id}")
                set_response = requests.get(
                    f'https://7tv.io/v3/emote-sets/{emote_set_id}',
                    timeout=10
                )
                
                if set_response.status_code == 200:
                    set_data = set_response.json()
                    emote_list = set_data.get('emotes', [])
                    LOGGER.info(f"Found {len(emote_list)} emotes in set")
                    
                    for emote in emote_list:
                        emote_name = emote.get('name', '')
                        if not emote_name:
                            continue
                        
                        # 7TV API v3 structure: emote can have 'data' object with 'host' object
                        # Or the emote might have the data directly
                        emote_data = emote.get('data', emote)  # Fallback to emote itself if no 'data' key
                        
                        # Try to get host from different possible locations
                        host = emote_data.get('host', {})
                        if not host and 'host' in emote:
                            host = emote.get('host', {})
                        
                        if not host:
                            # Try alternative structure: might have 'urls' or direct URL
                            if 'urls' in emote_data:
                                urls = emote_data['urls']
                                if isinstance(urls, list) and len(urls) > 0:
                                    file_url = urls[0] if isinstance(urls[0], str) else urls[0].get('url', '')
                                    if file_url:
                                        emotes[emote_name] = file_url
                                        LOGGER.debug(f"Added emote (alt structure): {emote_name} -> {file_url}")
                                continue
                            continue
                        
                        # Host has 'url' and 'files' array
                        host_url = host.get('url', '')
                        files = host.get('files', [])
                        
                        if not host_url:
                            continue
                        
                        # Find the best quality file (prefer 2x webp)
                        file_url = None
                        if files:
                            # Look for 2x webp first (56px width = 2x for 28px base)
                            for file in files:
                                if file.get('format', '').lower() == 'webp':
                                    width = file.get('width', 0)
                                    if width >= 56:  # 2x or higher
                                        file_name = file.get('name', '')
                                        if file_name:
                                            file_url = f"https:{host_url}/{file_name}"
                                            break
                            
                            # Fallback to first webp file
                            if not file_url:
                                for file in files:
                                    if file.get('format', '').lower() == 'webp':
                                        file_name = file.get('name', '')
                                        if file_name:
                                            file_url = f"https:{host_url}/{file_name}"
                                            break
                            
                            # Last resort: use first file
                            if not file_url and files:
                                file_name = files[0].get('name', '')
                                if file_name:
                                    file_url = f"https:{host_url}/{file_name}"
                        else:
                            # If no files array, try to construct URL (format: /2x.webp)
                            file_url = f"https:{host_url}/2x.webp"
                        
                        if file_url:
                            emotes[emote_name] = file_url
                            LOGGER.debug(f"Added emote: {emote_name} -> {file_url}")
                else:
                    LOGGER.warning(f"7TV emote set API returned status {set_response.status_code}: {set_response.text}")
            else:
                LOGGER.warning(f"No emote set ID found for user {streamer_name}")
        
        # Also get global emotes
        try:
            LOGGER.info("Fetching global 7TV emotes")
            global_response = requests.get(
                'https://7tv.io/v3/emote-sets/global',
                timeout=10
            )
            
            if global_response.status_code == 200:
                global_data = global_response.json()
                emote_list = global_data.get('emotes', [])
                LOGGER.info(f"Found {len(emote_list)} global emotes")
                
                for emote in emote_list:
                    emote_name = emote.get('name', '')
                    if not emote_name or emote_name in emotes:
                        continue
                    
                    # 7TV API v3 structure: emote can have 'data' object with 'host' object
                    emote_data = emote.get('data', emote)  # Fallback to emote itself if no 'data' key
                    
                    # Try to get host from different possible locations
                    host = emote_data.get('host', {})
                    if not host and 'host' in emote:
                        host = emote.get('host', {})
                    
                    if not host:
                        # Try alternative structure: might have 'urls' or direct URL
                        if 'urls' in emote_data:
                            urls = emote_data['urls']
                            if isinstance(urls, list) and len(urls) > 0:
                                file_url = urls[0] if isinstance(urls[0], str) else urls[0].get('url', '')
                                if file_url:
                                    emotes[emote_name] = file_url
                                    LOGGER.debug(f"Added global emote (alt structure): {emote_name} -> {file_url}")
                            continue
                        continue
                    
                    host_url = host.get('url', '')
                    files = host.get('files', [])
                    
                    if not host_url:
                        continue
                    
                    file_url = None
                    if files:
                        for file in files:
                            if file.get('format', '').lower() == 'webp':
                                width = file.get('width', 0)
                                if width >= 56:
                                    file_name = file.get('name', '')
                                    if file_name:
                                        file_url = f"https:{host_url}/{file_name}"
                                        break
                        
                        if not file_url:
                            for file in files:
                                if file.get('format', '').lower() == 'webp':
                                    file_name = file.get('name', '')
                                    if file_name:
                                        file_url = f"https:{host_url}/{file_name}"
                                        break
                        
                        if not file_url and files:
                            file_name = files[0].get('name', '')
                            if file_name:
                                file_url = f"https:{host_url}/{file_name}"
                    else:
                        file_url = f"https:{host_url}/2x.webp"
                    
                    if file_url:
                        emotes[emote_name] = file_url
            else:
                LOGGER.warning(f"Global 7TV emotes API returned status {global_response.status_code}")
        except Exception as global_error:
            LOGGER.warning(f"Could not fetch global 7TV emotes: {global_error}")
        
        LOGGER.info(f"Loaded {len(emotes)} total 7TV emotes for {streamer_name}")
        if len(emotes) == 0:
            LOGGER.warning("No 7TV emotes loaded! Check API responses above.")
        
        return jsonify({'emotes': emotes})
        
    except Exception as e:
        LOGGER.error(f"Error fetching 7TV emotes: {e}", exc_info=True)
        return jsonify({'emotes': {}, 'error': str(e)})


def run_flask_server():
    """Run the Flask web server."""
    try:
        LOGGER.info("Starting Flask server on http://localhost:5000")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        LOGGER.error(f"Flask server error: {e}")


if __name__ == "__main__":
    # Clear messages database on startup
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        # Ensure messages table exists first
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user TEXT NOT NULL,
                message TEXT NOT NULL,
                platform TEXT DEFAULT 'twitch',
                timestamp REAL DEFAULT (julianday('now'))
            )
        ''')
        # Clear all messages
        cursor.execute("DELETE FROM messages;")
        conn.commit()
        cursor.close()
        conn.close()
        LOGGER.info(f"Cleared messages database at {SQL_DB_PATH}")
    except Exception as e:
        LOGGER.warning(f"Could not clear messages database: {e}")
    
    # Clear old TTS file on startup to prevent playing old audio on overlay refresh
    TTS_FILE = 'tts.mp3'
    try:
        if os.path.exists(TTS_FILE):
            os.remove(TTS_FILE)
            LOGGER.info("Cleared old TTS file on startup")
    except Exception as e:
        LOGGER.warning(f"Could not clear TTS file: {e}")
    
    # Start bot in background thread
    LOGGER.info("Starting bot...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start Spotify overlay in background thread
    LOGGER.info("Starting Spotify overlay...")
    spotify_thread = threading.Thread(target=run_spotify_overlay, daemon=True)
    spotify_thread.start()
    
    # Start Flask server in background thread
    LOGGER.info("Starting Flask server...")
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    LOGGER.info("=" * 60)
    LOGGER.info("All services started!")
    LOGGER.info("=" * 60)
    LOGGER.info("Bot: Running in background")
    LOGGER.info("Spotify Overlay: Writing to spotify_now_playing.txt")
    LOGGER.info("Flask Server: http://localhost:5000")
    LOGGER.info("Chat Overlay: http://localhost:5000/chat_overlay.html")
    LOGGER.info("Links Manager: http://localhost:5000/links")
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
