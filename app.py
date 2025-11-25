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
