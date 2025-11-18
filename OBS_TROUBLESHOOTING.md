# OBS Browser Source Troubleshooting

If messages show in browser but not in OBS, try these steps:

## Quick Fixes (Try These First)

### 1. Clear OBS Browser Cache
1. In OBS, right-click your **Browser Source**
2. Click **Interact**
3. In the browser window that opens, press `Ctrl+Shift+Delete`
4. Clear cache/cookies
5. Close the interact window
6. Right-click Browser Source → **Refresh**

### 2. Check Browser Source Settings
1. Right-click Browser Source → **Properties**
2. Verify:
   - **URL**: `http://localhost:5000` (exactly this, no trailing slash)
   - **Width**: `1920` (or your canvas width)
   - **Height**: `1080` (or your canvas height)
   - **Shutdown source when not visible**: ✅ Checked
   - **Refresh browser when scene becomes active**: ✅ Checked

### 3. Check Source Order
- Make sure Browser Source is **above** other sources in the list
- Other sources might be covering it

### 4. Reset Transform
1. Right-click Browser Source → **Transform** → **Reset Transform**
2. This resets position/scale

## Advanced Debugging

### 5. Use Interact Mode to Debug
1. Right-click Browser Source → **Interact**
2. This opens the overlay in a browser window
3. Press `F12` to open developer console
4. Check for JavaScript errors
5. Check Network tab to see if API calls are working

### 6. Test with Visible Background
Temporarily change the overlay to have a visible background:

Edit `chat_overlay.html` line 16:
```css
background: rgba(255, 0, 0, 0.3); /* Red tint for debugging */
```

This helps you see if the overlay is loading but messages aren't showing.

### 7. Check OBS Logs
1. In OBS: **Help** → **Log Files** → **View Current Log**
2. Look for errors related to Browser Source

### 8. Try Different URL Format
Sometimes OBS prefers:
- `http://127.0.0.1:5000` instead of `http://localhost:5000`

### 9. Check if Server is Accessible
In OBS Interact mode (right-click → Interact), try:
- Opening `http://localhost:5000/api/messages` directly
- You should see JSON data

### 10. Verify Messages Exist
Run this in Python to check database:
```python
import sqlite3
conn = sqlite3.connect('messages.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM messages")
print(f"Messages in DB: {cursor.fetchone()[0]}")
conn.close()
```

## Common Issues

### Issue: Blank/White Screen
- **Cause**: JavaScript error or API not accessible
- **Fix**: Check Interact mode console (F12) for errors

### Issue: Overlay Loads but No Messages
- **Cause**: API returning empty array or JavaScript not running
- **Fix**: 
  1. Check Interact mode → Network tab → See if `/api/messages` returns data
  2. Check Console for JavaScript errors
  3. Verify messages exist in database

### Issue: Messages Show Then Disappear
- **Cause**: Messages timing out (30 seconds default)
- **Fix**: This is normal behavior, new messages should appear

### Issue: Wrong Size/Position
- **Cause**: Browser Source dimensions or transform settings
- **Fix**: 
  1. Reset Transform
  2. Set exact width/height in Browser Source properties
  3. Use Transform → Fit to Screen

## Testing Checklist

- [ ] Server is running (`python chat_overlay_server.py`)
- [ ] Can access `http://localhost:5000` in regular browser
- [ ] Can see messages in regular browser
- [ ] Browser Source URL is exactly `http://localhost:5000`
- [ ] Browser Source width/height are set correctly
- [ ] Cleared OBS browser cache
- [ ] Checked Interact mode for errors
- [ ] Messages exist in database
- [ ] API endpoint returns data (`http://localhost:5000/api/messages`)

## Still Not Working?

1. **Create a simple test overlay:**
   Create `test_simple.html`:
   ```html
   <!DOCTYPE html>
   <html>
   <body style="background: red; color: white; font-size: 50px; padding: 50px;">
       TEST - If you see this, Browser Source works!
   </body>
   </html>
   ```
   Serve it and test in OBS. If this doesn't show, it's an OBS configuration issue.

2. **Check OBS version:**
   - Update OBS to latest version
   - Browser Source might be disabled in older versions

3. **Try alternative:**
   - Use Window Capture instead (capture browser window)
   - Less ideal but works as fallback

