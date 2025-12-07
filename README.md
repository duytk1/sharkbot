# Sharkbot

A comprehensive Twitch and YouTube streaming bot with AI chat responses, Text-to-Speech (TTS), OBS overlays, and cross-platform chat integration.

## Features

### 🤖 Core Functionality
- **Dual Platform Support**: Works with both Twitch and YouTube live streams
- **AI Chat Responses**: Uses OpenAI to generate witty, context-aware responses when mentioned
- **Text-to-Speech (TTS)**: Converts AI responses to speech for OBS overlays
- **Cross-Platform Chat**: Automatically forwards messages between Twitch and YouTube chat
- **Event Handling**: Responds to follows, subscriptions, raids, ad breaks, and more

### 🎨 OBS Integration
- **Chat Overlay**: Real-time chat display with 7TV emote support
- **TTS Overlay**: Plays AI-generated speech in OBS
- **Spotify Integration**: Displays currently playing song
- **Links Manager**: Web interface to manage stream links

### 💬 Commands
- `!pob` - Path of Exile build link
- `!profile` - Path of Exile profile link
- `!build` - Build guide link
- `!vid` - Video link
- `!discord` - Discord server invite
- `!ign` - In-game name
- `!mb` - Marketplace link
- `!lurk` - Get a joke and thank you message
- `!search <query>` - Search using OpenAI
- `!trick`

## Prerequisites

- Python 3.8 or higher
- Twitch account with bot credentials
- OpenAI API key
- (Optional) YouTube API credentials for YouTube integration
- (Optional) Spotify API credentials for Spotify overlay

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sharkbot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root with the following variables:
   ```env
   # Twitch API Credentials
   CLIENT_ID=your_twitch_client_id
   CLIENT_SECRET=your_twitch_client_secret
   OWNER_ID=your_twitch_user_id
   STREAMER_NAME=your_twitch_username
   
   # OpenAI
   OPENAI_API_KEY=your_openai_api_key
   
   # Database
   SQL_CONNECT=messages.db
   
   # YouTube (Optional)
   YOUTUBE_VIDEO_ID=your_youtube_video_id_or_url
   YOUTUBE_LIVE_CHAT_ID=your_youtube_live_chat_id
   
   # Spotify (Optional)
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIFY_CALLBACK_URI=http://localhost:5000/callback
   
   # 7TV Emotes (Optional)
   7TV_USER_ID=your_7tv_user_id
   ```

## Setup Instructions

### Twitch Bot Setup

1. Go to [Twitch Developer Console](https://dev.twitch.tv/console)
2. Create a new application
3. Get your `CLIENT_ID` and `CLIENT_SECRET`
4. Get your `OWNER_ID` (Twitch User ID) from [Twitch API](https://dev.twitch.tv/docs/api/reference#get-users)
5. Add these to your `.env` file

### YouTube Integration (Optional)

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable "YouTube Data API v3"

2. **Create OAuth Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Create OAuth 2.0 Client ID (Desktop app type)
   - Download the JSON file and save as `client_secret.json`

3. **Authenticate**
   - Run the authentication script (if available) or let the bot handle it automatically
   - The bot will create `youtube_token.pickle` on first run

4. **Get Live Chat ID**
   - Start a YouTube live stream
   - Find the Live Chat ID in YouTube Studio
   - Add to `.env`: `YOUTUBE_LIVE_CHAT_ID=your_chat_id`

### Spotify Integration (Optional)

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Get `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
4. Set redirect URI to `http://localhost:5000/callback`
5. Add credentials to `.env`

## Usage

### Starting the Bot

Run the main application:
```bash
python app.py
```

This will start:
- Twitch/YouTube bot
- Flask web server (for overlays)
- Spotify overlay (if configured)

### Accessing Web Interfaces

Once running, access these URLs:

- **Chat Overlay**: `http://localhost:5000/chat_overlay.html`
- **Links Manager**: `http://localhost:5000/links`
- **TTS Generator**: `http://localhost:5000/tts`

### OBS Setup

1. **Chat Overlay**
   - Add a Browser Source in OBS
   - URL: `http://localhost:5000/chat_overlay.html`
   - Width: 1920, Height: 1080 (adjust as needed)

2. **TTS Audio**
   - The TTS audio is automatically played through the overlay
   - No additional OBS setup needed

3. **Spotify Overlay**
   - Add a Text Source in OBS
   - Read from file: `spotify_now_playing.txt`
   - Enable "Read from file" option

## How It Works

### Chat Processing Flow

1. **Message Reception**: Bot receives messages from Twitch/YouTube
2. **Cross-Platform Forwarding**: Messages are forwarded to the other platform
3. **AI Processing**: If the bot is mentioned, it generates a response using OpenAI
4. **TTS Generation**: AI responses are converted to speech
5. **Overlay Display**: Chat and TTS are displayed in OBS

### TTS Queue System

The bot uses a smart queue system to prevent TTS interruptions:
- Messages are queued and processed sequentially
- Each TTS waits for the previous one to finish
- Prevents audio cutting and restarting issues

## File Structure

```
sharkbot/
├── app.py                 # Main Flask application
├── sharkbot.py            # Twitch/YouTube bot logic
├── sharkai.py             # OpenAI integration
├── spotify_overlay.py     # Spotify integration
├── chat_overlay.html      # OBS chat overlay
├── links_manager.html     # Links management interface
├── tts.html               # TTS generator interface
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
└── README.md             # This file
```

## Configuration

### Customizing AI Responses

Edit `sharkai.py` to modify the AI prompt and behavior:
- Change the system prompt
- Adjust message history length
- Modify response style

### Customizing Commands

Edit `sharkbot.py` to add or modify commands:
- Add new `@commands.command()` functions
- Customize command responses
- Add new link types

### TTS Settings

In `sharkbot.py`, you can modify:
- `bot_language`: Change TTS voice (default: "en-AU-NatashaNeural")
- TTS queue wait times
- File cleanup intervals

## Troubleshooting

### Bot Not Responding
- Check that all environment variables are set correctly
- Verify Twitch/YouTube credentials are valid
- Check logs for error messages

### TTS Not Playing
- Ensure the overlay is loaded in OBS
- Check that `tts.mp3` is being generated
- Verify file permissions

### YouTube Messages Not Sending
- Verify `youtube_token.pickle` exists and is valid
- Check that `YOUTUBE_LIVE_CHAT_ID` is correct
- Ensure YouTube stream is live

### Cross-Platform Chat Not Working
- Verify both platforms are configured
- Check that bot has permission to send messages
- Ensure messages aren't being filtered as spam

## Security Notes

⚠️ **Important**: Never commit these files to version control:
- `.env` - Contains all API keys and secrets
- `youtube_token.pickle` - Contains OAuth tokens
- `client_secret.json` - Contains Google OAuth credentials
- `*.db` - Database files with user data

These are already in `.gitignore` for your protection.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is for personal/streaming use. Modify and use as needed.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review error logs
3. Verify all credentials are correct
4. Ensure all dependencies are installed

---

**Happy Streaming! 🦈**
