# Testing Guide for Chat Overlay

## Quick Test (Recommended)

1. **Install dependencies** (if not already installed):
   ```bash
   pip install flask flask-cors requests
   ```

2. **Run the test script**:
   ```bash
   python test_overlay.py
   ```
   
   This will:
   - Add test messages to your database
   - Test the API endpoint
   - Test the HTML page
   - Guide you through the testing process

3. **Open in browser**:
   - Open `http://localhost:5000` in your web browser
   - You should see test messages displayed

## Manual Testing Steps

### Step 1: Start the Overlay Server

Open a terminal and run:
```bash
python chat_overlay_server.py
```

You should see:
```
Starting chat overlay server on http://localhost:5000
Add this URL to OBS as a Browser Source: http://localhost:5000
 * Running on http://0.0.0.0:5000
```

### Step 2: Test the API Endpoint

Open another terminal and test the API:

**Using curl:**
```bash
curl http://localhost:5000/api/messages
```

**Using PowerShell:**
```powershell
Invoke-WebRequest -Uri http://localhost:5000/api/messages | Select-Object -ExpandProperty Content
```

**Using Python:**
```python
import requests
response = requests.get("http://localhost:5000/api/messages")
print(response.json())
```

You should see JSON with chat messages like:
```json
[
  {
    "user": "viewer1",
    "message": "Hello!",
    "platform": "twitch",
    "id": 1
  },
  ...
]
```

### Step 3: Test the HTML Overlay

1. Open your web browser
2. Navigate to: `http://localhost:5000`
3. You should see the chat overlay with messages displayed

### Step 4: Add Test Messages (Optional)

If you want to add test messages to the database manually:

```python
import sqlite3

conn = sqlite3.connect('messages.db')
cursor = conn.cursor()

# Add a Twitch message
cursor.execute(
    "INSERT INTO messages (from_user, message, platform) VALUES (?, ?, ?)",
    ("test_user", "This is a test message from Twitch!", "twitch")
)

# Add a YouTube message
cursor.execute(
    "INSERT INTO messages (from_user, message, platform) VALUES (?, ?, ?)",
    ("yt_user", "This is a test message from YouTube!", "youtube")
)

conn.commit()
conn.close()
```

Then refresh the browser to see the new messages.

### Step 5: Test in OBS

1. Open OBS Studio
2. Add a **Browser Source**
3. Set URL to: `http://localhost:5000`
4. Set width: `1920` (or your stream width)
5. Set height: `1080` (or your stream height)
6. You should see the overlay in OBS

## Testing with Real Messages

To test with real messages from your bot:

1. Make sure your bot (`sharkbot.py`) is running
2. Send messages in Twitch chat or YouTube chat
3. The messages should appear in the overlay automatically

## Troubleshooting

**Server won't start:**
- Check if port 5000 is already in use: `netstat -ano | findstr :5000`
- Change the port in `chat_overlay_server.py` if needed

**No messages showing:**
- Check if messages exist in database: `python -c "import sqlite3; conn = sqlite3.connect('messages.db'); print(conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0])"`
- Make sure the database file path is correct

**API returns empty array:**
- Check if messages table has data
- Verify the platform column exists: `python -c "import sqlite3; conn = sqlite3.connect('messages.db'); conn.execute('ALTER TABLE messages ADD COLUMN platform TEXT DEFAULT \"twitch\"'); conn.commit()"`

**Overlay not updating:**
- Check browser console for errors (F12)
- Verify the API is returning data
- Check POLL_INTERVAL in `chat_overlay.html` (default: 2000ms)

## Expected Behavior

- Messages should appear at the bottom of the screen
- Twitch messages should have purple border and "TW" badge
- YouTube messages should have red border and "YT" badge
- Messages should fade out after 30 seconds
- New messages should slide in from the left
- Maximum 20 messages displayed at once

