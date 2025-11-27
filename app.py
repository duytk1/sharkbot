import asyncio
import threading
import sqlite3
import logging

from sharkbot import start_bot
import time
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
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


@app.route('/api/7tv/debug')
def debug_7tv():
    """Debug endpoint to test 7TV API ID-based lookups."""
    import requests
    import json
    
    seven_tv_user_id = os.environ.get("7TV_USER_ID", None)
    emote_set_id = os.environ.get("7TV_EMOTE_SET_ID", None)
    
    debug_info = {
        '7TV_USER_ID': seven_tv_user_id,
        '7TV_EMOTE_SET_ID': emote_set_id,
        'tests': []
    }
    
    # Test 1: 7TV User ID lookup
    if seven_tv_user_id:
        try:
            response = requests.get(
                f'https://7tv.io/v3/users/{seven_tv_user_id}',
                timeout=10
            )
            debug_info['tests'].append({
                'method': '7TV User ID',
                'url': f'https://7tv.io/v3/users/{seven_tv_user_id}',
                'status': response.status_code,
                'success': response.status_code == 200,
                'response_keys': list(response.json().keys()) if response.status_code == 200 else None,
                'response_preview': json.dumps(response.json(), indent=2)[:1000] if response.status_code == 200 else response.text[:500]
            })
        except Exception as e:
            debug_info['tests'].append({
                'method': '7TV User ID',
                'url': f'https://7tv.io/v3/users/{seven_tv_user_id}',
                'error': str(e)
            })
    else:
        debug_info['tests'].append({
            'method': '7TV User ID',
            'status': 'skipped',
            'message': '7TV_USER_ID not set in environment variables'
        })
    
    # Test 2: Emote Set ID lookup
    if emote_set_id:
        try:
            response = requests.get(
                f'https://7tv.io/v3/emote-sets/{emote_set_id}',
                timeout=10
            )
            debug_info['tests'].append({
                'method': 'Emote Set ID',
                'url': f'https://7tv.io/v3/emote-sets/{emote_set_id}',
                'status': response.status_code,
                'success': response.status_code == 200,
                'emote_count': len(response.json().get('emotes', [])) if response.status_code == 200 else None,
                'response_preview': json.dumps(response.json(), indent=2)[:1000] if response.status_code == 200 else response.text[:500]
            })
        except Exception as e:
            debug_info['tests'].append({
                'method': 'Emote Set ID',
                'url': f'https://7tv.io/v3/emote-sets/{emote_set_id}',
                'error': str(e)
            })
    else:
        debug_info['tests'].append({
            'method': 'Emote Set ID',
            'status': 'skipped',
            'message': '7TV_EMOTE_SET_ID not set in environment variables'
        })
    
    debug_info['instructions'] = {
        'finding_7tv_user_id': 'Go to https://7tv.app, log in, go to your profile. The user ID is in the URL or API responses.',
        'finding_emote_set_id': 'Go to https://7tv.app, log in, go to your emote set. The ID is in the URL (e.g., /emote-sets/1234567890abcdef) or in the API response.',
        'environment_variables': {
            '7TV_USER_ID': 'Set this to your 7TV user ID for direct lookup',
            '7TV_EMOTE_SET_ID': 'Set this to your emote set ID to bypass user lookup'
        }
    }
    
    return jsonify(debug_info)


@app.route('/api/7tv/emotes')
def get_7tv_emotes():
    """Get 7TV emotes using ID-based lookups."""
    import requests
    import json
    
    # Get IDs from environment variables
    seven_tv_user_id = os.environ.get("7TV_USER_ID", None)
    emote_set_id = os.environ.get("7TV_EMOTE_SET_ID", None)
    
    try:
        emotes = {}
        user_data = None
        
        # Try to get user data by 7TV User ID
        if seven_tv_user_id:
            LOGGER.info(f"Fetching 7TV user data by User ID: {seven_tv_user_id}")
            user_response = requests.get(
                f'https://7tv.io/v3/users/{seven_tv_user_id}',
                timeout=10
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                LOGGER.info(f"✓ Successfully found 7TV user: {seven_tv_user_id}")
                LOGGER.info(f"7TV user data keys: {list(user_data.keys())}")
            else:
                LOGGER.warning(f"7TV user API returned status {user_response.status_code}: {user_response.text[:500]}")
        
        # Get emote set ID from user data or environment variable
        emote_set_id = os.environ.get("7TV_EMOTE_SET_ID", None)
        
        # If we have user data, try to extract emote set ID from it
        if user_data and not emote_set_id:
            # Try different possible locations for emote_set
            if 'emote_set' in user_data:
                emote_set_obj = user_data['emote_set']
                if isinstance(emote_set_obj, dict):
                    emote_set_id = emote_set_obj.get('id')
                    LOGGER.info(f"Found emote_set.id: {emote_set_id}")
                elif isinstance(emote_set_obj, str):
                    emote_set_id = emote_set_obj
                    LOGGER.info(f"Found emote_set (string): {emote_set_id}")
            
            if not emote_set_id and 'emote_sets' in user_data:
                emote_sets = user_data['emote_sets']
                if isinstance(emote_sets, list) and len(emote_sets) > 0:
                    first_set = emote_sets[0]
                    if isinstance(first_set, str):
                        emote_set_id = first_set
                        LOGGER.info(f"Found emote_sets[0] (string): {emote_set_id}")
                    elif isinstance(first_set, dict):
                        emote_set_id = first_set.get('id')
                        LOGGER.info(f"Found emote_sets[0].id: {emote_set_id}")
                elif isinstance(emote_sets, dict):
                    emote_set_id = emote_sets.get('id')
                    LOGGER.info(f"Found emote_sets.id: {emote_set_id}")
            
            # Check connections for emote set
            if not emote_set_id and 'connections' in user_data:
                connections = user_data['connections']
                if isinstance(connections, list) and len(connections) > 0:
                    for conn in connections:
                        if isinstance(conn, dict) and conn.get('platform') == 'TWITCH':
                            if 'emote_set' in conn:
                                emote_set_obj = conn['emote_set']
                                if isinstance(emote_set_obj, dict):
                                    emote_set_id = emote_set_obj.get('id')
                                elif isinstance(emote_set_obj, str):
                                    emote_set_id = emote_set_obj
                                if emote_set_id:
                                    LOGGER.info(f"Found emote_set from connection: {emote_set_id}")
                                    break
        
        # Fetch emotes from emote set if we have an ID
        if emote_set_id:
                LOGGER.info(f"Fetching 7TV emote set: {emote_set_id}")
                set_response = requests.get(
                    f'https://7tv.io/v3/emote-sets/{emote_set_id}',
                    timeout=10
                )
                
                if set_response.status_code == 200:
                    set_data = set_response.json()
                    LOGGER.info(f"Emote set data keys: {list(set_data.keys())}")
                    emote_list = set_data.get('emotes', [])
                    LOGGER.info(f"Found {len(emote_list)} emotes in set")
                    
                    if len(emote_list) > 0:
                        # Log first emote structure for debugging
                        LOGGER.debug(f"First emote structure: {json.dumps(emote_list[0], indent=2)[:500]}")
                    
                    for emote in emote_list:
                        emote_name = emote.get('name', '')
                        if not emote_name:
                            continue
                        
                        # 7TV API v3: emote has 'data' object
                        emote_data = emote.get('data', {})
                        if not emote_data:
                            LOGGER.debug(f"Emote {emote_name} has no data object")
                            continue
                        
                        # Get host from data
                        host = emote_data.get('host', {})
                        if not host:
                            LOGGER.debug(f"Emote {emote_name} has no host in data")
                            continue
                        
                        # Host has 'url' and 'files' array
                        host_url = host.get('url', '')
                        files = host.get('files', [])
                        
                        if not host_url:
                            LOGGER.debug(f"Emote {emote_name} has no host URL")
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
                            LOGGER.warning(f"Could not construct URL for emote: {emote_name}")
                else:
                    LOGGER.warning(f"7TV emote set API returned status {set_response.status_code}: {set_response.text[:500]}")
        else:
            if user_data:
                LOGGER.warning(f"No emote set ID found in user data. User data structure: {json.dumps(user_data, indent=2)[:500]}")
        
        # If we have an emote set ID from environment variable and haven't loaded emotes yet, try using it
        if not emotes and emote_set_id:
            LOGGER.info(f"Fetching emotes from emote set ID: {emote_set_id}")
            try:
                set_response = requests.get(
                    f'https://7tv.io/v3/emote-sets/{emote_set_id}',
                    timeout=10
                )
                if set_response.status_code == 200:
                    set_data = set_response.json()
                    emote_list = set_data.get('emotes', [])
                    LOGGER.info(f"Found {len(emote_list)} emotes in emote set")
                    
                    for emote in emote_list:
                        emote_name = emote.get('name', '')
                        if not emote_name:
                            continue
                        
                        emote_data = emote.get('data', {})
                        if not emote_data:
                            continue
                        
                        host = emote_data.get('host', {})
                        if not host:
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
                            LOGGER.debug(f"Added emote from set: {emote_name} -> {file_url}")
            except Exception as set_error:
                LOGGER.warning(f"Failed to load emote set: {set_error}")
        
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
                    
                    emote_data = emote.get('data', {})
                    if not emote_data:
                        continue
                    
                    host = emote_data.get('host', {})
                    if not host:
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
            LOGGER.warning(f"Could not fetch global 7TV emotes: {global_error}", exc_info=True)
        
        LOGGER.info(f"Loaded {len(emotes)} total 7TV emotes")
        if len(emotes) == 0:
            LOGGER.warning("No 7TV emotes loaded! Set 7TV_USER_ID or 7TV_EMOTE_SET_ID environment variables.")
        else:
            # Log first few emote names
            sample_emotes = list(emotes.keys())[:5]
            LOGGER.info(f"Sample emotes loaded: {sample_emotes}")
        
        return jsonify({
            'emotes': emotes,
            'user_found': user_data is not None,
            'emote_count': len(emotes)
        })
        
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
