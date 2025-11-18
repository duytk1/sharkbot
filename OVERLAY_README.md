# Chat Overlay for OBS

This overlay displays both Twitch and YouTube chat messages in OBS Studio.

## Setup

1. **Install dependencies:**
   ```bash
   pip install flask flask-cors
   ```

2. **Start the overlay server:**
   ```bash
   python chat_overlay_server.py
   ```
   The server will start on `http://localhost:5000`

3. **Add to OBS:**
   - In OBS Studio, add a new **Browser Source**
   - Set the URL to: `http://localhost:5000`
   - Set width: `1920` (or your stream width)
   - Set height: `1080` (or your stream height)
   - Check "Shutdown source when not visible" (optional)
   - Check "Refresh browser when scene becomes active" (optional)

## Customization

### Adjusting Message Display

Edit `chat_overlay.html` to customize:
- **MAX_MESSAGES**: Maximum number of messages to show (default: 20)
- **POLL_INTERVAL**: How often to check for new messages in milliseconds (default: 2000ms)
- **MESSAGE_TIMEOUT**: How long messages stay visible in milliseconds (default: 30000ms)

### Styling

The overlay uses CSS that you can customize:
- Colors: Twitch purple (#9146ff) and YouTube red (#ff0000)
- Font: Segoe UI (change in the CSS)
- Background: Semi-transparent black with blur effect
- Position: Messages appear at the bottom of the screen

### Changing Port

If port 5000 is in use, edit `chat_overlay_server.py`:
```python
app.run(host='0.0.0.0', port=5000, debug=False)  # Change 5000 to your desired port
```

Then update the URL in OBS and the API_URL in `chat_overlay.html`.

## Features

- ✅ Displays both Twitch and YouTube chat messages
- ✅ Color-coded by platform (purple for Twitch, red for YouTube)
- ✅ Platform badges (TW/YT) for easy identification
- ✅ Auto-fade out old messages
- ✅ Smooth animations
- ✅ Real-time updates via polling
- ✅ Transparent background (perfect for overlays)

## Troubleshooting

**Messages not appearing:**
- Make sure the bot is running and receiving messages
- Check that `chat_overlay_server.py` is running
- Verify the database file exists and has messages

**Overlay not showing in OBS:**
- Make sure the Browser Source URL is correct
- Check that the server is accessible (try opening the URL in a browser)
- Verify OBS Browser Source is enabled

**Styling issues:**
- Clear OBS browser cache: Right-click Browser Source → Interact → Clear cache
- Refresh the browser source in OBS

