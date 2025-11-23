"""
Web server for OBS chat overlay.
Serves an HTML overlay that displays both Twitch and YouTube chat messages.
"""
import sqlite3
import os
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv
import logging
import requests
import time

load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow OBS browser source to access the API

LOGGER = logging.getLogger("ChatOverlay")
SQL_DB_PATH = os.environ.get("SQL_CONNECT", "messages.db")

# Cache for 7TV emotes
_7TV_EMOTE_CACHE = {}
_7TV_CACHE_TIMESTAMP = 0
_7TV_CACHE_TTL = 3600  # Cache for 1 hour

# Cache for Twitch emotes
_TWITCH_EMOTE_CACHE = {}
_TWITCH_CACHE_TIMESTAMP = 0
_TWITCH_CACHE_TTL = 3600  # Cache for 1 hour

# Fallback: Known global Twitch emote IDs (common emotes)
# Format: {emote_name: emote_id}
# These are some popular global Twitch emotes as fallback if API fails
_TWITCH_GLOBAL_EMOTES_FALLBACK = {
    'kappa': '25',
    'pogchamp': '305954156',
    'lul': '425618',
    'omegalul': '583089f4737a8a61f5d9f643',
    'monkas': '145315',
    'pepehands': '166263',
    'pepega': '5b77ac3af7bddc567b1d5fb2',
    'pepepains': '230106',
    'pepepls': '5b77ac3af7bddc567b1d5fb2',
    'kappapride': '55338b3c6895877209d2d8d0',
    '4head': '354',
    'biblethump': '86',
    'bloodtrail': '196652',
    'coolstorybob': '123171',
    'failfish': '360',
    'kreygasm': '41',
    'mrdestructoid': '28',
    'pogchamp': '305954156',
    'residentsleeper': '245',
    'seemsgood': '64138',
    'smorc': '52',
    'trihard': '120232',
    'wutface': '28087',
}

def _add_fallback_global_emotes(emotes_dict):
    """Add fallback global Twitch emotes when API fails."""
    for name, emote_id in _TWITCH_GLOBAL_EMOTES_FALLBACK.items():
        if name not in emotes_dict:  # Don't override existing
            image_url = f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/dark/2.0"
            emotes_dict[name] = image_url
    LOGGER.info(f"Added {len(_TWITCH_GLOBAL_EMOTES_FALLBACK)} fallback Twitch emotes")

def fetch_7tv_emotes(user_id=None):
    """Fetch 7TV emotes for a Twitch user or global emotes."""
    global _7TV_EMOTE_CACHE, _7TV_CACHE_TIMESTAMP
    
    # Check cache
    current_time = time.time()
    if _7TV_EMOTE_CACHE and (current_time - _7TV_CACHE_TIMESTAMP) < _7TV_CACHE_TTL:
        return _7TV_EMOTE_CACHE
    
    emotes = {}
    
    try:
        # Fetch global emotes - 7TV API v3 structure
        try:
            response = requests.get('https://7tv.io/v3/emote-sets/global', timeout=10)
            if response.status_code == 200:
                data = response.json()
                LOGGER.debug(f"Global emote set response type: {type(data)}")
                
                # 7TV API v3: response is an emote set object with 'emotes' array
                emote_list = data.get('emotes', [])
                
                for emote in emote_list:
                    name = emote.get('name', '').lower()
                    if not name:
                        continue
                    
                    # 7TV API v3 structure: emote has 'data' with 'host' and 'files'
                    emote_data = emote.get('data', emote)
                    if not emote_data:
                        continue
                    
                    host = emote_data.get('host', {})
                    if not host:
                        continue
                    
                    # Get files array
                    files = host.get('files', [])
                    if not files:
                        continue
                    
                    # Build URL - host.url is a string like "//cdn.7tv.app/emote/..."
                    base_url = host.get('url', '')
                    if not base_url:
                        continue
                    
                    # Ensure base_url starts with //
                    if not base_url.startswith('//'):
                        base_url = '//' + base_url.lstrip('/')
                    
                    # Find best quality file (prefer 2x/webp, then any webp)
                    image_url = None
                    for file in files:
                        file_format = file.get('format', '')
                        file_name = file.get('name', '')
                        width = file.get('width', 0)
                        
                        if file_format == 'webp':
                            # Prefer 2x (56px width) or files with '2x' in name
                            if width == 56 or '2x' in file_name.lower():
                                image_url = f"https:{base_url}/{file_name}"
                                break
                    
                    # Fallback to first webp file
                    if not image_url:
                        for file in files:
                            if file.get('format') == 'webp':
                                image_url = f"https:{base_url}/{file.get('name', '')}"
                                break
                    
                    # Last resort: use any file
                    if not image_url and files:
                        image_url = f"https:{base_url}/{files[0].get('name', '')}"
                    
                    if image_url:
                        emotes[name] = image_url
                        
            else:
                LOGGER.warning(f"Failed to fetch global emotes: HTTP {response.status_code}")
        except Exception as e:
            LOGGER.warning(f"Error fetching global 7TV emotes: {e}", exc_info=True)
        
        # Fetch channel-specific emotes if user_id is provided
        if user_id:
            try:
                response = requests.get(f'https://7tv.io/v3/users/twitch/{user_id}', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    LOGGER.debug(f"Channel emote response type: {type(data)}")
                    
                    # Get emote set from user data
                    emote_set = data.get('emote_set', {})
                    if not emote_set:
                        # Try alternative structure
                        emote_set = data.get('emotes', {})
                    
                    emote_list = emote_set.get('emotes', []) if isinstance(emote_set, dict) else []
                    
                    for emote in emote_list:
                        name = emote.get('name', '').lower()
                        if not name:
                            continue
                        
                        emote_data = emote.get('data', emote)
                        if not emote_data:
                            continue
                        
                        host = emote_data.get('host', {})
                        if not host:
                            continue
                        
                        files = host.get('files', [])
                        if not files:
                            continue
                        
                        base_url = host.get('url', '')
                        if not base_url:
                            continue
                        
                        if not base_url.startswith('//'):
                            base_url = '//' + base_url.lstrip('/')
                        
                        image_url = None
                        for file in files:
                            if file.get('format') == 'webp':
                                width = file.get('width', 0)
                                file_name = file.get('name', '')
                                if width == 56 or '2x' in file_name.lower():
                                    image_url = f"https:{base_url}/{file_name}"
                                    break
                        
                        if not image_url:
                            for file in files:
                                if file.get('format') == 'webp':
                                    image_url = f"https:{base_url}/{file.get('name', '')}"
                                    break
                        
                        if not image_url and files:
                            image_url = f"https:{base_url}/{files[0].get('name', '')}"
                        
                        if image_url:
                            emotes[name] = image_url  # Channel emotes override global
                else:
                    LOGGER.warning(f"Failed to fetch channel emotes: HTTP {response.status_code}")
            except Exception as e:
                LOGGER.warning(f"Error fetching channel 7TV emotes for user {user_id}: {e}", exc_info=True)
        
        _7TV_EMOTE_CACHE = emotes
        _7TV_CACHE_TIMESTAMP = current_time
        LOGGER.info(f"Fetched {len(emotes)} 7TV emotes")
        if len(emotes) > 0:
            # Log first few emote names for debugging
            sample_emotes = list(emotes.keys())[:5]
            LOGGER.info(f"Sample emotes: {sample_emotes}")
        else:
            LOGGER.warning("No emotes fetched. Check API response structure.")
        
    except Exception as e:
        LOGGER.error(f"Error fetching 7TV emotes: {e}", exc_info=True)
    
    return emotes

def fetch_twitch_emotes(user_id=None, client_id=None):
    """Fetch Twitch emotes (global and channel-specific)."""
    global _TWITCH_EMOTE_CACHE, _TWITCH_CACHE_TIMESTAMP
    
    # Check cache
    current_time = time.time()
    if _TWITCH_EMOTE_CACHE and (current_time - _TWITCH_CACHE_TIMESTAMP) < _TWITCH_CACHE_TTL:
        return _TWITCH_EMOTE_CACHE
    
    emotes = {}
    
    if not client_id:
        LOGGER.warning("CLIENT_ID not set, skipping Twitch emotes")
        return emotes
    
    try:
        # Twitch Helix API requires Client-ID header
        # Note: Some endpoints may require OAuth, but chat emotes should work with just Client-ID
        headers = {
            'Client-ID': client_id,
            'Accept': 'application/json'
        }
        
        # Log for debugging
        LOGGER.info(f"Fetching Twitch emotes with Client-ID: {client_id[:10]}..." if client_id else "No Client-ID")
        
        # Fetch global Twitch emotes
        try:
            response = requests.get('https://api.twitch.tv/helix/chat/emotes/global', headers=headers, timeout=10)
            LOGGER.debug(f"Global Twitch emotes API response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                emote_list = data.get('data', [])
                LOGGER.debug(f"Found {len(emote_list)} global Twitch emotes")
                
                for emote in emote_list:
                    name = emote.get('name', '').lower()
                    emote_id = emote.get('id', '')
                    
                    if name and emote_id:
                        # Twitch emote URL format: https://static-cdn.jtvnw.net/emoticons/v2/{id}/default/dark/2.0
                        # Use 2.0 for better quality
                        image_url = f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/dark/2.0"
                        emotes[name] = image_url
            elif response.status_code == 401:
                LOGGER.error("Twitch API authentication failed. Check CLIENT_ID.")
                LOGGER.error(f"Response: {response.text[:200]}")
                # Try using a fallback method with known global emotes
                LOGGER.info("Attempting fallback: using known global Twitch emotes")
                _add_fallback_global_emotes(emotes)
            elif response.status_code == 403:
                LOGGER.error("Twitch API access forbidden. Check CLIENT_ID permissions.")
                LOGGER.error(f"Response: {response.text[:200]}")
                # Try using a fallback method
                LOGGER.info("Attempting fallback: using known global Twitch emotes")
                _add_fallback_global_emotes(emotes)
            else:
                LOGGER.warning(f"Failed to fetch global Twitch emotes: HTTP {response.status_code}")
                LOGGER.warning(f"Response: {response.text[:200]}")
                # Try fallback on any error
                LOGGER.info("Attempting fallback: using known global Twitch emotes")
                _add_fallback_global_emotes(emotes)
        except Exception as e:
            LOGGER.warning(f"Error fetching global Twitch emotes: {e}", exc_info=True)
            # Try fallback on exception
            LOGGER.info("Attempting fallback: using known global Twitch emotes")
            _add_fallback_global_emotes(emotes)
        
        # Fetch channel-specific Twitch emotes if user_id is provided
        if user_id:
            try:
                response = requests.get(
                    f'https://api.twitch.tv/helix/chat/emotes?broadcaster_id={user_id}',
                    headers=headers,
                    timeout=10
                )
                LOGGER.debug(f"Channel Twitch emotes API response: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    emote_list = data.get('data', [])
                    LOGGER.debug(f"Found {len(emote_list)} channel Twitch emotes")
                    
                    for emote in emote_list:
                        name = emote.get('name', '').lower()
                        emote_id = emote.get('id', '')
                        
                        if name and emote_id:
                            # Channel emotes override global
                            image_url = f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/dark/2.0"
                            emotes[name] = image_url
                elif response.status_code == 401:
                    LOGGER.error("Twitch API authentication failed for channel emotes. Check CLIENT_ID.")
                elif response.status_code == 403:
                    LOGGER.error("Twitch API access forbidden for channel emotes. Check CLIENT_ID permissions.")
                else:
                    LOGGER.warning(f"Failed to fetch channel Twitch emotes: HTTP {response.status_code}")
                    LOGGER.warning(f"Response: {response.text[:200]}")
            except Exception as e:
                LOGGER.warning(f"Error fetching channel Twitch emotes for user {user_id}: {e}", exc_info=True)
        
        _TWITCH_EMOTE_CACHE = emotes
        _TWITCH_CACHE_TIMESTAMP = current_time
        LOGGER.info(f"Fetched {len(emotes)} Twitch emotes")
        if len(emotes) > 0:
            sample_emotes = list(emotes.keys())[:5]
            LOGGER.info(f"Sample Twitch emotes: {sample_emotes}")
        else:
            LOGGER.warning("No Twitch emotes fetched. Check logs above for errors.")
        
    except Exception as e:
        LOGGER.error(f"Error fetching Twitch emotes: {e}", exc_info=True)
    
    return emotes

def get_recent_messages(limit=50, max_age_hours=24):
    """Get recent chat messages from database.
    
    Args:
        limit: Maximum number of messages to return
        max_age_hours: Only return messages newer than this many hours (default 24)
    """
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ensure platform and timestamp columns exist
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN platform TEXT DEFAULT 'twitch'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN timestamp REAL DEFAULT (julianday('now'))")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Calculate cutoff time (current time minus max_age_hours)
        # SQLite uses Julian day numbers, so we subtract hours/24
        cutoff_time = f"julianday('now') - {max_age_hours}/24.0"
        
        # Only include messages with valid timestamps that are within the age limit
        # Exclude NULL timestamps to avoid showing old messages without timestamps
        cursor.execute(f"""
            SELECT from_user, message, platform, id, timestamp
            FROM messages 
            WHERE timestamp IS NOT NULL AND timestamp > {cutoff_time}
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        
        messages = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts and reverse to show oldest first
        result = [
            {
                'user': row['from_user'],
                'message': row['message'],
                'platform': row['platform'] or 'twitch',
                'id': row['id'],
                'timestamp': row.get('timestamp')
            }
            for row in reversed(messages)
        ]
        return result
    except Exception as e:
        LOGGER.error(f"Error fetching messages: {e}")
        return []

@app.route('/api/messages')
def get_messages():
    """API endpoint to get recent chat messages."""
    # Get max_age_hours from query parameter, default to 1 hour for initial load
    # This ensures we only show messages from the last hour on initial load
    max_age_hours = request.args.get('max_age_hours', default=1, type=float)
    messages = get_recent_messages(limit=50, max_age_hours=max_age_hours)
    return jsonify(messages)

@app.route('/api/tts')
def get_tts():
    """API endpoint to check if TTS file exists and get its timestamp."""
    tts_file = 'tts.mp3'
    if os.path.exists(tts_file):
        return jsonify({
            'exists': True,
            'url': '/tts.mp3',
            'timestamp': os.path.getmtime(tts_file)
        })
    return jsonify({'exists': False})

@app.route('/api/7tv-emotes')
def get_7tv_emotes():
    """API endpoint to get 7TV emotes."""
    user_id = os.environ.get("OWNER_ID")
    emotes = fetch_7tv_emotes(user_id)
    return jsonify(emotes)

@app.route('/api/twitch-emotes')
def get_twitch_emotes():
    """API endpoint to get Twitch emotes."""
    user_id = os.environ.get("OWNER_ID")
    client_id = os.environ.get("CLIENT_ID")
    emotes = fetch_twitch_emotes(user_id, client_id)
    return jsonify(emotes)

@app.route('/api/all-emotes')
def get_all_emotes():
    """API endpoint to get all emotes (7TV + Twitch combined)."""
    user_id = os.environ.get("OWNER_ID")
    client_id = os.environ.get("CLIENT_ID")
    
    # Fetch both emote sets
    stv_emotes = fetch_7tv_emotes(user_id)
    twitch_emotes = fetch_twitch_emotes(user_id, client_id)
    
    # Combine (Twitch emotes take precedence if there's a conflict)
    all_emotes = {**stv_emotes, **twitch_emotes}
    
    return jsonify(all_emotes)

@app.route('/api/7tv-emotes/debug')
def debug_7tv_emotes():
    """Debug endpoint to test 7TV API directly."""
    import json
    try:
        # Test global emotes
        response = requests.get('https://7tv.io/v3/emote-sets/global', timeout=10)
        global_data = {
            'status_code': response.status_code,
            'has_data': response.status_code == 200,
            'keys': list(response.json().keys()) if response.status_code == 200 else None
        }
        
        # Test channel emotes if user_id exists
        user_id = os.environ.get("OWNER_ID")
        channel_data = None
        if user_id:
            try:
                ch_response = requests.get(f'https://7tv.io/v3/users/twitch/{user_id}', timeout=10)
                channel_data = {
                    'status_code': ch_response.status_code,
                    'has_data': ch_response.status_code == 200,
                    'keys': list(ch_response.json().keys()) if ch_response.status_code == 200 else None
                }
            except:
                pass
        
        return jsonify({
            'global': global_data,
            'channel': channel_data,
            'cached_emotes_count': len(_7TV_EMOTE_CACHE),
            'sample_cached_emotes': list(_7TV_EMOTE_CACHE.keys())[:10] if _7TV_EMOTE_CACHE else []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/twitch-emotes/debug')
def debug_twitch_emotes():
    """Debug endpoint to test Twitch API directly."""
    import json
    try:
        client_id = os.environ.get("CLIENT_ID")
        user_id = os.environ.get("OWNER_ID")
        
        if not client_id:
            return jsonify({'error': 'CLIENT_ID not set'}), 400
        
        headers = {
            'Client-ID': client_id,
            'Accept': 'application/json'
        }
        
        # Test global emotes
        response = requests.get('https://api.twitch.tv/helix/chat/emotes/global', headers=headers, timeout=10)
        global_data = {
            'status_code': response.status_code,
            'has_data': response.status_code == 200,
            'response_text': response.text[:500] if response.status_code != 200 else None,
            'emote_count': len(response.json().get('data', [])) if response.status_code == 200 else 0
        }
        
        # Test channel emotes
        channel_data = None
        if user_id:
            try:
                ch_response = requests.get(
                    f'https://api.twitch.tv/helix/chat/emotes?broadcaster_id={user_id}',
                    headers=headers,
                    timeout=10
                )
                channel_data = {
                    'status_code': ch_response.status_code,
                    'has_data': ch_response.status_code == 200,
                    'response_text': ch_response.text[:500] if ch_response.status_code != 200 else None,
                    'emote_count': len(ch_response.json().get('data', [])) if ch_response.status_code == 200 else 0
                }
            except Exception as e:
                channel_data = {'error': str(e)}
        
        return jsonify({
            'client_id_set': bool(client_id),
            'user_id_set': bool(user_id),
            'global': global_data,
            'channel': channel_data,
            'cached_emotes_count': len(_TWITCH_EMOTE_CACHE),
            'sample_cached_emotes': list(_TWITCH_EMOTE_CACHE.keys())[:10] if _TWITCH_EMOTE_CACHE else []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tts.mp3')
def serve_tts():
    """Serve the TTS audio file."""
    return send_from_directory('.', 'tts.mp3', mimetype='audio/mpeg')

def init_links_table():
    """Initialize the links table in the database."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        LOGGER.error(f"Error initializing links table: {e}")

def get_link(key: str, default: str = "") -> str:
    """Get a link value from the database."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM links WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
    except Exception as e:
        LOGGER.error(f"Error getting link {key}: {e}")
        return default

def set_link(key: str, value: str) -> bool:
    """Set a link value in the database."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO links (key, value)
            VALUES (?, ?)
        ''', (key, value))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        LOGGER.error(f"Error setting link {key}: {e}")
        return False

def get_all_links() -> dict:
    """Get all links from the database."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM links")
        results = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in results}
    except Exception as e:
        LOGGER.error(f"Error getting all links: {e}")
        return {}

# Initialize links table on module load
init_links_table()

@app.route('/api/links', methods=['GET'])
def api_get_links():
    """API endpoint to get all links."""
    links = get_all_links()
    return jsonify(links)

@app.route('/api/links', methods=['POST'])
def api_set_links():
    """API endpoint to set links."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        results = {}
        for key, value in data.items():
            if set_link(key, value):
                results[key] = 'success'
            else:
                results[key] = 'error'
        
        return jsonify({'status': 'success', 'results': results})
    except Exception as e:
        LOGGER.error(f"Error setting links: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/links/<key>', methods=['GET'])
def api_get_link(key):
    """API endpoint to get a specific link."""
    value = get_link(key)
    return jsonify({'key': key, 'value': value})

@app.route('/links')
def links_page():
    """Serve the links management page."""
    return send_from_directory('.', 'links_manager.html')

@app.route('/')
def index():
    """Serve the overlay HTML page."""
    return send_from_directory('.', 'chat_overlay.html')

if __name__ == '__main__':
    LOGGER.info("Starting chat overlay server on http://localhost:5000")
    LOGGER.info("Add this URL to OBS as a Browser Source: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

