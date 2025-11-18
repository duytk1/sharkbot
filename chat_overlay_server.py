"""
Web server for OBS chat overlay.
Serves an HTML overlay that displays both Twitch and YouTube chat messages.
"""
import sqlite3
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow OBS browser source to access the API

LOGGER = logging.getLogger("ChatOverlay")
SQL_DB_PATH = os.environ.get("SQL_CONNECT", "messages.db")

def get_recent_messages(limit=50):
    """Get recent chat messages from database."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ensure platform column exists
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN platform TEXT DEFAULT 'twitch'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        cursor.execute("""
            SELECT from_user, message, platform, id
            FROM messages 
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
                'id': row['id']
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
    messages = get_recent_messages(limit=50)
    return jsonify(messages)

@app.route('/')
def index():
    """Serve the overlay HTML page."""
    return send_from_directory('.', 'chat_overlay.html')

if __name__ == '__main__':
    LOGGER.info("Starting chat overlay server on http://localhost:5000")
    LOGGER.info("Add this URL to OBS as a Browser Source: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

