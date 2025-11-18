# Chat Overlay Customization Guide

## Quick Size Changes in OBS

**Easiest method:**
1. Select the Browser Source in OBS
2. Drag the corners to resize
3. Or right-click → **Transform** → **Edit Transform** → Set exact width/height

## CSS Customization

Edit `chat_overlay.html` to customize sizes. Key properties:

### Message Box Size

**Line 47:** `max-width: 600px;`
- Controls maximum width of each message box
- Increase for wider messages, decrease for narrower
- Example: `max-width: 800px;` for wider boxes

**Line 50:** `font-size: 16px;`
- Controls text size in messages
- Increase for larger text, decrease for smaller
- Example: `font-size: 20px;` for bigger text

**Line 42:** `padding: 8px 12px;`
- Controls internal spacing of message boxes
- First number = top/bottom, second = left/right
- Example: `padding: 12px 16px;` for more spacing

### Container Spacing

**Line 34:** `padding: 20px;`
- Controls distance from screen edges
- Increase to move messages away from edges
- Example: `padding: 40px;` for more margin

**Line 35:** `gap: 8px;`
- Controls spacing between messages
- Increase for more space between messages
- Example: `gap: 12px;` for more separation

### Badge Size

**Line 66:** `font-size: 10px;`
- Controls platform badge (TW/YT) size
- Example: `font-size: 12px;` for larger badges

## Common Size Presets

### Small Overlay (Compact)
```css
.chat-message {
    max-width: 400px;
    font-size: 14px;
    padding: 6px 10px;
}
#chat-container {
    padding: 15px;
    gap: 6px;
}
```

### Large Overlay (Easy to Read)
```css
.chat-message {
    max-width: 800px;
    font-size: 20px;
    padding: 12px 16px;
}
#chat-container {
    padding: 30px;
    gap: 12px;
}
```

### Medium Overlay (Balanced - Current)
```css
.chat-message {
    max-width: 600px;
    font-size: 16px;
    padding: 8px 12px;
}
#chat-container {
    padding: 20px;
    gap: 8px;
}
```

## Position Changes

To change where messages appear:

**Line 33:** `justify-content: flex-end;`
- `flex-end` = bottom (current)
- `flex-start` = top
- `center` = middle

**Line 34:** `padding: 20px;`
- Adjust individual sides:
  - `padding: 20px 20px 40px 20px;` = more space at bottom
  - `padding: 40px 20px 20px 20px;` = more space at top

## After Making Changes

1. Save `chat_overlay.html`
2. In OBS: Right-click Browser Source → **Refresh**
3. Or restart the overlay server

## Tips

- Use browser dev tools (F12) to test changes live
- Start with small changes and test
- Consider your stream resolution when setting sizes
- Larger text = easier to read but takes more screen space

