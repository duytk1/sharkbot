import asyncio
import logging
import sqlite3
import os
import threading
import time
import queue
import shutil
import asqlite
import twitchio
from twitchio.ext import commands
from twitchio import eventsub
import pygame
import winsound
from gtts import gTTS
import io
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qs
import requests
import json

from sharkai import SharkAI

from dotenv import load_dotenv

load_dotenv()

LOGGER: logging.Logger = logging.getLogger("Bot")

try:
    import pytchat

    YOUTUBE_CHAT_AVAILABLE = True
except ImportError:
    YOUTUBE_CHAT_AVAILABLE = False
    LOGGER.warning(
        "pytchat not installed. YouTube chat functionality will be disabled."
    )

# Configuration
CLIENT_ID: str = os.environ.get("CLIENT_ID")
CLIENT_SECRET: str = os.environ.get("CLIENT_SECRET")
BOT_ID = os.environ.get("OWNER_ID")
OWNER_ID = os.environ.get("OWNER_ID")
SQL_DB_PATH = os.environ.get("SQL_CONNECT", "messages.db")


def _extract_youtube_video_id(raw_value: str | None) -> str:
    """Allow users to paste a whole YouTube URL or just the video ID."""
    if not raw_value:
        return ""

    value = raw_value.strip()
    if not value:
        return ""

    lowered = value.lower()
    if "youtube.com" in lowered or "youtu.be" in lowered:
        parsed = urlparse(value)

        if parsed.netloc.endswith("youtu.be"):
            candidate = parsed.path.lstrip("/").split("/")[0]
            return candidate or ""

        query_params = parse_qs(parsed.query)
        if "v" in query_params and query_params["v"]:
            return query_params["v"][0]

        # Handle /live/<video_id> paths
        if "/live/" in parsed.path:
            return parsed.path.split("/live/")[1].split("/")[0]

        # As fallback, take last path segment
        segments = [segment for segment in parsed.path.split("/") if segment]
        if segments:
            return segments[-1]

        return ""

    # Already an ID – trim query fragments
    return value.split("&")[0].split("?")[0]


YOUTUBE_VIDEO_ID = _extract_youtube_video_id(
    os.environ.get("YOUTUBE_VIDEO_ID")
)  # YouTube live stream video ID

# Constants
MAX_MESSAGE_HISTORY = 30
MAX_MESSAGE_LENGTH = 900
LONG_MESSAGE_THRESHOLD = 500
FIRST_MESSAGE_CHUNK = 480
SECOND_MESSAGE_CHUNK = 990
TTS_FILE = "tts.mp3"
BOT_NAME = "sharkothehuman"
STREAMER_NAME = os.environ.get("STREAMER_NAME", "sharko51")

# Default links (fallback if not in database)
DEFAULT_LINKS = {
    "pob": "https://pobb.in/V3nQhzR2IxTl",
    "profile": "https://www.pathofexile.com/account/view-profile/cbera-0095/characters",
    "ign": "sharko_can_breed",
    "build": "https://www.youtube.com/watch?v=nAQ1Y-Jz888&t",
    "vid": "https://www.twitch.tv/sharko51/clip/PeppyCooperativeLasagnaRiPepperonis-TqCjkjPL7Pegl2LB",
    "mb": "",
}
# TTS Language: gTTS uses language codes like 'en' (English), 'en-au' (Australian English), etc.
# Common options: 'en' (US), 'en-uk' (UK), 'en-au' (Australia), 'en-ca' (Canada)
bot_language = "en-au"  # Australian English


def init_links_database():
    """Initialize links database with default values if empty."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        # Ensure links table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Check if table is empty
        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]

        # If empty, populate with defaults
        if count == 0:
            for key, value in DEFAULT_LINKS.items():
                if value:  # Only insert non-empty defaults
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO links (key, value)
                        VALUES (?, ?)
                    """,
                        (key, value),
                    )
            conn.commit()
            LOGGER.info("Initialized links database with default values")

        conn.close()
    except Exception as e:
        LOGGER.warning(f"Error initializing links database: {e}")


def get_link_from_db(key: str) -> str:
    """Get a link from the database, with fallback to default."""
    try:
        conn = sqlite3.connect(SQL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM links WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return result[0]
    except Exception as e:
        LOGGER.error(f"Error getting link {key} from database: {e}")

    # Fallback to default
    return DEFAULT_LINKS.get(key, "")


# Initialize pygame mixer once
pygame.mixer.init()


class Bot(commands.Bot):
    def __init__(self, *, token_database: asqlite.Pool) -> None:
        self.token_database = token_database
        super().__init__(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="!",
        )

    async def setup_hook(self) -> None:
        component = MyComponent(self)
        await self.add_component(component)

        # Initialize TTS queue (needs event loop to exist)
        component._tts_queue = asyncio.Queue()
        
        # Start TTS queue processor
        component._tts_processor_task = asyncio.create_task(component._process_tts_queue())

        # Start YouTube chat monitoring if configured
        if YOUTUBE_CHAT_AVAILABLE and YOUTUBE_VIDEO_ID:
            await component.start_youtube_chat()

        # Define all subscriptions in a list for cleaner code
        subscriptions = [
            eventsub.ChatMessageSubscription(
                broadcaster_user_id=OWNER_ID, user_id=BOT_ID
            ),
            eventsub.StreamOnlineSubscription(broadcaster_user_id=OWNER_ID),
            eventsub.AdBreakBeginSubscription(
                broadcaster_user_id=OWNER_ID, moderator_user_id=OWNER_ID
            ),
            eventsub.ChannelRaidSubscription(to_broadcaster_user_id=OWNER_ID),
            eventsub.ChannelFollowSubscription(
                broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID
            ),
            eventsub.ChannelSubscriptionGiftSubscription(broadcaster_user_id=OWNER_ID),
            eventsub.AutomodMessageHoldV2Subscription(
                broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID
            ),
            eventsub.ChannelBanSubscription(broadcaster_user_id=OWNER_ID),
            eventsub.ChannelSubscribeSubscription(broadcaster_user_id=OWNER_ID),
        ]

        # Subscribe to all events
        for subscription in subscriptions:
            await self.subscribe_websocket(payload=subscription)

    async def add_token(self, token: str, refresh: str) -> None:
        resp = await super().add_token(token, refresh)
        query = """
            INSERT INTO tokens (user_id, token, refresh)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                token = excluded.token,
                refresh = excluded.refresh;
        """
        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))
        LOGGER.info("Added token to the database for user: %s", resp.user_id)

    async def load_tokens(self, path: str | None = None) -> None:
        async with self.token_database.acquire() as connection:
            rows: list[sqlite3.Row] = await connection.fetchall(
                """SELECT * from tokens"""
            )

        for row in rows:
            await self.add_token(row["token"], row["refresh"])

    async def setup_database(self) -> None:
        query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
        async with self.token_database.acquire() as connection:
            await connection.execute(query)

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)


class MyComponent(commands.Component):
    def __init__(self, bot: Bot):
        self.bot = bot
        self._db_path = SQL_DB_PATH
        self._youtube_chat_task = None
        self._youtube_chat_thread = None
        self._youtube_chat_queue = None
        self._youtube_chat_stop_event = None
        self._tts_lock = threading.Lock()  # Lock for TTS generation to prevent concurrent overwrites
        self._tts_queue = None  # Queue for TTS requests (initialized in setup)
        self._tts_processing = False  # Flag to track if TTS is currently being processed
        self._tts_processor_task = None  # Task that processes the TTS queue
        self._current_tts_file = None  # Track the current TTS file being played

    @contextmanager
    def _get_db_connection(self):
        """Get a database connection as a context manager."""
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        chatter_name = payload.chatter.name
        streamer_name = payload.broadcaster.name
        message = payload.text

        if not message:
            return

        # Get first word once for efficiency
        first_word = message.split(" ", 1)[0].lower()
        is_clear_command = first_word == "clear" and chatter_name == streamer_name
        is_mention = first_word in ("sharko")
        is_chatter = chatter_name != streamer_name
        is_command = message.startswith("!")

        # Database operations
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                if is_clear_command:
                    cursor.execute("DELETE FROM messages;")
                else:
                    # Store all messages (including streamer)
                    # Ensure platform and timestamp columns exist
                    try:
                        cursor.execute(
                            "ALTER TABLE messages ADD COLUMN platform TEXT DEFAULT 'twitch'"
                        )
                        conn.commit()
                    except sqlite3.OperationalError:
                        pass  # Column already exists
                    try:
                        cursor.execute(
                            "ALTER TABLE messages ADD COLUMN timestamp REAL DEFAULT (julianday('now'))"
                        )
                        conn.commit()
                    except sqlite3.OperationalError:
                        pass  # Column already exists

                    # Optimize: combine count check and delete in one query if needed
                    cursor.execute("SELECT COUNT(*) FROM messages")
                    count = cursor.fetchone()[0]
                    if count >= MAX_MESSAGE_HISTORY:
                        cursor.execute(
                            "DELETE FROM messages WHERE id = (SELECT id FROM messages ORDER BY id ASC LIMIT 1)"
                        )
                    cursor.execute(
                        "INSERT INTO messages (from_user, message, platform, timestamp) VALUES (?, ?, ?, julianday('now'))",
                        (chatter_name, message, "twitch"),
                    )
        except Exception as e:
            LOGGER.error(f"Database error in event_message: {e}")

        print(f"[TWITCH] [{chatter_name}]: {message}")

        # Send Twitch message to YouTube chat (skip bot messages and commands)
        if YOUTUBE_VIDEO_ID and chatter_name != BOT_NAME and not is_command and chatter_name != streamer_name:
            youtube_message = f"{chatter_name} from twitch: {message}"
            await self.send_youtube_message(youtube_message)

        if is_chatter and chatter_name != BOT_NAME:
            winsound.PlaySound("*", winsound.SND_ALIAS)

        # Skip further processing for commands - let twitchio's command system handle them
        if is_command:
            return

        if is_mention:
            # Remove "sharko" prefix from message before sending to AI
            cleaned_message = message.removeprefix("sharko").strip()
            if not cleaned_message:
                cleaned_message = message  # Fallback if removal leaves nothing

            response = SharkAI.chat_with_openai(
                f"new message from {chatter_name}: {cleaned_message}, response"
            )

            # Send response in chunks if needed
            await self.send_message(payload, response)

            # Create TTS text - just use the response to avoid repetition
            tts_text = response

            await self.make_tts(tts_text)
            self.play_sound(TTS_FILE)

    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        # Event dispatched when we go live
        await payload.broadcaster.send_message(
            sender=self.bot.bot_id,
            message=f"{payload.broadcaster} is yapping again",
        )

    @commands.Component.listener()
    async def event_ad_break(self, payload: twitchio.ChannelAdBreakBegin) -> None:
        LOGGER.info(f"Processing ad break event (duration: {payload.duration}s)")

        prompt = f"an ad break has begun for {payload.duration}, thank the viewers for their patience. from then on treat the chat room as a clean new one."

        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM messages")
                count = cursor.fetchone()[0]
                LOGGER.info(f"Message count for ad break: {count}")
                if count > 0:
                    prompt += " recap the chat and mention the chatters by ."

                await self.send_message(payload, SharkAI.chat_with_openai(prompt))
                cursor.execute("DELETE FROM messages;")
        except Exception as e:
            LOGGER.error(f"Database error in event_ad_break: {e}")

    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        message = SharkAI.chat_with_openai(
            f"{payload.from_broadcaster.name} is raiding, thank them"
        )
        await self.send_message(payload, message)

    @commands.Component.listener()
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        message = SharkAI.chat_with_openai(
            f"{payload.user} followed, thank them properly"
        )
        await self.send_message(payload, message)
        await self.make_tts(message)
        self.play_sound(TTS_FILE)

    @commands.Component.listener()
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        subscription_tier = int(payload.tier) / 1000
        message = SharkAI.chat_with_openai(
            f"{payload.user} just subscribed with tier {subscription_tier}, thank them"
        )
        await self.send_message(payload, message)
        await self.make_tts(message)
        self.play_sound(TTS_FILE)

    @commands.Component.listener()
    async def event_subscription_gift(
        self, payload: twitchio.ChannelSubscriptionGift
    ) -> None:
        message = SharkAI.chat_with_openai(
            f"{payload.user} just gifted {payload.total} subs, thank them"
        )
        await self.send_message(payload, message)
        await self.make_tts(message)
        self.play_sound(TTS_FILE)

    @commands.Component.listener()
    async def event_automod_message_hold(
        self, payload: twitchio.AutomodMessageHold
    ) -> None:
        winsound.PlaySound("*", winsound.SND_ALIAS)
        print("automodded message: " + payload.text)

    @commands.Component.listener()
    async def event_ban(self, payload: twitchio.ChannelBan) -> None:
        """Handle ban/timeout events and delete user's messages from database."""
        try:
            # Get the username from the payload
            # Try to get the name attribute, otherwise convert to string
            if hasattr(payload, 'user'):
                if hasattr(payload.user, 'name'):
                    banned_user_name = payload.user.name
                else:
                    banned_user_name = str(payload.user)
            else:
                LOGGER.warning("Ban payload does not have 'user' attribute")
                banned_user_name = None
            
            if banned_user_name:
                LOGGER.info(f"User {banned_user_name} was banned/timed out. Deleting their messages from database.")
                
                # Delete all messages from this user in the database
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM messages WHERE from_user = ?",
                        (banned_user_name,)
                    )
                    deleted_count = cursor.rowcount
                    LOGGER.info(f"Deleted {deleted_count} messages from {banned_user_name}")
            
            await self.send_message(payload, "RIPBOZO")
        except Exception as e:
            LOGGER.error(f"Error handling ban/timeout event: {e}", exc_info=True)
            # Still send the message even if deletion fails
            try:
                await self.send_message(payload, "RIPBOZO")
            except Exception as send_error:
                LOGGER.error(f"Error sending ban message: {send_error}")

    @commands.command()
    async def pob(self, ctx: commands.Context) -> None:
        try:
            print("here")
            link = get_link_from_db("pob")
            if link and link.strip():
                response = f"{ctx.chatter.mention} {link}"
                await ctx.send(response)
            else:
                error_msg = f"{ctx.chatter.mention} POB link not configured. Use the links manager at http://localhost:5000/links to set it."

                await ctx.send(error_msg)
        except Exception as e:
            LOGGER.error(f"Error in !pob command: {e}", exc_info=True)
            try:
                await ctx.send(
                    f"{ctx.chatter.mention} Error retrieving POB link. Please try again later."
                )
            except Exception as send_error:
                LOGGER.error(f"Failed to send error message: {send_error}")

    @commands.Component.listener()
    async def event_command_error(
        self, ctx: commands.Context, error: Exception
    ) -> None:
        """Handle command errors."""
        LOGGER.error(
            f"Command error in {ctx.command.name if ctx.command else 'unknown'} command from {ctx.chatter.name}: {error}",
            exc_info=True,
        )

    @commands.command()
    async def profile(self, ctx: commands.Context) -> None:
        link = get_link_from_db("profile")
        if link:
            await ctx.send(f"{ctx.chatter.mention} " + link)
        else:
            await ctx.send(
                f"{ctx.chatter.mention} Profile link not configured. Use the links manager to set it."
            )

    @commands.command()
    async def build(self, ctx: commands.Context) -> None:
        link = get_link_from_db("build")
        if link:
            await ctx.send(f"{ctx.chatter.mention} " + link)
        else:
            await ctx.send(
                f"{ctx.chatter.mention} Build link not configured. Use the links manager to set it."
            )

    @commands.command()
    async def vid(self, ctx: commands.Context) -> None:
        link = get_link_from_db("vid")
        if link:
            await ctx.send(f"{ctx.chatter.mention} " + link)
        else:
            await ctx.send(
                f"{ctx.chatter.mention} Video link not configured. Use the links manager to set it."
            )

    @commands.command()
    async def discord(self, ctx: commands.Context) -> None:
        await ctx.send(
            f"{ctx.chatter.mention} " + " https://discord.com/invite/ZyDXVXdHWM"
        )

    @commands.command()
    async def ign(self, ctx: commands.Context) -> None:
        link = get_link_from_db("ign")
        if link:
            await ctx.send(f"{ctx.chatter.mention}  " + link)
        else:
            await ctx.send(
                f"{ctx.chatter.mention} IGN not configured. Use the links manager to set it."
            )

    @commands.command()
    async def mb(self, ctx: commands.Context) -> None:
        link = get_link_from_db("mb")
        if link:
            await ctx.send(f"{ctx.chatter.mention} " + link)
        else:
            await ctx.send(
                f"{ctx.chatter.mention} MB link not configured. Use the links manager to set it."
            )

    @commands.command()
    async def lurk(self, ctx: commands.Context) -> None:
        message = SharkAI.chat_with_openai(
            f"{ctx.chatter.name} is lurking, tell them a joke and thank for lurking"
        )
        await ctx.send(f"{ctx.chatter.mention} " + message)

    @commands.command()
    async def search(self, ctx: commands.Context, *, query: str) -> None:
        try:
            result = SharkAI.search_open_ai(query)
            # Extract the response content from the OpenAI response object
            if hasattr(result, "choices") and len(result.choices) > 0:
                response_text = (
                    result.choices[0].message.content
                    if hasattr(result.choices[0].message, "content")
                    else str(result)
                )
            else:
                response_text = str(result)
            await ctx.send(f"{ctx.chatter.mention} {response_text}")
        except Exception as e:
            LOGGER.error(f"Search error: {e}")
            await ctx.send(f"{ctx.chatter.mention} Error performing search.")

    @commands.command()
    async def trick(self, ctx: commands.Context) -> None:
        await ctx.send(
            f"{ctx.chatter.mention}"
            + " https://www.twitch.tv/sharko51/clip/ElegantPeacefulRaccoonAllenHuhu-4SNxLLMor3NV6m11"
        )

    async def process_chat_message(
        self, chatter_name: str, message: str, platform: str = "twitch"
    ) -> None:
        """Process chat messages from any platform (Twitch/YouTube)."""
        if not message:
            return

        # Optimize: get first word once
        first_word = message.split(" ", 1)[0].lower()
        chatter_lower = chatter_name.lower()
        streamer_lower = STREAMER_NAME.lower()
        is_clear_command = first_word == "clear" and chatter_lower == streamer_lower
        is_mention = first_word in ("sharko", "@sharko51")
        is_chatter = chatter_lower != streamer_lower
        # Database operations
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                if is_clear_command:
                    cursor.execute("DELETE FROM messages;")
                else:
                    # Store all messages (including streamer)
                    # Ensure platform and timestamp columns exist
                    try:
                        cursor.execute(
                            "ALTER TABLE messages ADD COLUMN platform TEXT DEFAULT 'twitch'"
                        )
                        conn.commit()
                    except sqlite3.OperationalError:
                        pass  # Column already exists
                    try:
                        cursor.execute(
                            "ALTER TABLE messages ADD COLUMN timestamp REAL DEFAULT (julianday('now'))"
                        )
                        conn.commit()
                    except sqlite3.OperationalError:
                        pass  # Column already exists

                    # Optimize: combine count check and delete in one query if needed
                    cursor.execute("SELECT COUNT(*) FROM messages")
                    count = cursor.fetchone()[0]
                    if count >= MAX_MESSAGE_HISTORY:
                        cursor.execute(
                            "DELETE FROM messages WHERE id = (SELECT id FROM messages ORDER BY id ASC LIMIT 1)"
                        )
                    cursor.execute(
                        "INSERT INTO messages (from_user, message, platform, timestamp) VALUES (?, ?, ?, julianday('now'))",
                        (chatter_name, message, platform),
                    )
        except Exception as e:
            LOGGER.error(f"Database error in process_chat_message: {e}")

        print(f"[{platform.upper()}] [{chatter_name}]: {message}")

        # Send YouTube message to Twitch chat (skip bot messages and commands)
        if platform == "youtube" and chatter_name != BOT_NAME and not message.startswith("!") and chatter_name.lower() != STREAMER_NAME.lower():
            twitch_message = f"{chatter_name} from youtube: {message}"
            await self.send_twitch_message(twitch_message)

        if is_chatter and chatter_name != BOT_NAME:
            winsound.PlaySound("*", winsound.SND_ALIAS)

        if is_mention:
            # Remove mention prefixes from message before sending to AI
            cleaned_message = (
                message.removeprefix("@sharko51").removeprefix("sharko").strip()
            )
            if not cleaned_message:
                cleaned_message = message  # Fallback if removal leaves nothing

            response = SharkAI.chat_with_openai(
                f"new message from {chatter_name} on {platform}: {cleaned_message}, response"
            )

            # For YouTube, we can't send messages back directly, but we can log it
            if platform == "youtube":
                LOGGER.info(f"AI Response to {chatter_name}: {response}")
            else:
                # For Twitch, we need the payload to send messages
                # This will be handled in event_message
                pass

            # Create TTS text - just use the response to avoid repetition
            tts_text = response

            await self.make_tts(tts_text)
            self.play_sound(TTS_FILE)

    async def start_youtube_chat(self) -> None:
        """Start monitoring YouTube live chat."""
        if not YOUTUBE_CHAT_AVAILABLE:
            LOGGER.warning("pytchat not available. YouTube chat monitoring disabled.")
            return

        if not YOUTUBE_VIDEO_ID:
            LOGGER.info("YOUTUBE_VIDEO_ID not set. YouTube chat monitoring disabled.")
            return

        LOGGER.info(f"Starting YouTube chat monitoring for video: {YOUTUBE_VIDEO_ID}")

        # Create queue and stop event for thread communication
        self._youtube_chat_queue = queue.Queue()
        self._youtube_chat_stop_event = threading.Event()

        # Start the monitoring thread (runs pytchat in a separate thread to avoid signal handler issues)
        self._youtube_chat_thread = threading.Thread(
            target=self._youtube_chat_thread_worker,
            daemon=True,
            args=(
                YOUTUBE_VIDEO_ID,
                self._youtube_chat_queue,
                self._youtube_chat_stop_event,
            ),
        )
        self._youtube_chat_thread.start()

        # Start async task to process messages from the queue
        self._youtube_chat_task = asyncio.create_task(
            self._process_youtube_chat_queue()
        )

    def _youtube_chat_thread_worker(
        self, video_id: str, msg_queue: queue.Queue, stop_event: threading.Event
    ) -> None:
        """Worker thread that runs pytchat (must be in a thread to avoid signal handler issues)."""
        chat = None
        # Polling configuration: start with 5 seconds, increase on errors (exponential backoff)
        poll_interval = 10.0  # 10 seconds is a reasonable default for live chat
        max_poll_interval = 30.0  # Cap at 30 seconds max
        error_count = 0

        try:
            # Create chat object with interruptable=False to disable signal handlers
            # This allows it to work in non-main threads
            chat = pytchat.create(video_id=video_id, interruptable=False)
            LOGGER.info("YouTube chat thread started")

            while not stop_event.is_set():
                try:
                    if not chat.is_alive():
                        LOGGER.warning("YouTube chat is no longer alive")
                        break

                    # Get chat items (blocking operation)
                    message_count = 0
                    for c in chat.get().sync_items():
                        if stop_event.is_set():
                            break

                        # Put message data in queue for async processing
                        msg_queue.put(
                            {
                                "chatter_name": c.author.name,
                                "message": c.message,
                                "timestamp": c.datetime,
                            }
                        )
                        message_count += 1

                    # Reset error count and poll interval on successful poll
                    if error_count > 0:
                        error_count = 0
                        poll_interval = 5.0  # Reset to default

                    # Poll every N seconds (5s default, longer if there were recent errors)
                    # This reduces API requests and respects rate limits
                    time.sleep(poll_interval)

                except Exception as e:
                    error_count += 1
                    LOGGER.error(f"Error in YouTube chat thread: {e}")

                    if stop_event.is_set():
                        break

                    # Exponential backoff: increase wait time on consecutive errors
                    # This helps avoid overwhelming the API during issues
                    poll_interval = min(poll_interval * 1.5, max_poll_interval)
                    LOGGER.info(
                        f"Backing off: waiting {poll_interval:.1f}s before retry (error count: {error_count})"
                    )
                    time.sleep(poll_interval)

        except Exception as e:
            LOGGER.error(f"YouTube chat thread error: {e}")
        finally:
            if chat:
                try:
                    if hasattr(chat, "terminate"):
                        chat.terminate()
                except Exception as e:
                    LOGGER.debug(f"Error cleaning up chat: {e}")
            LOGGER.info("YouTube chat thread stopped")

    async def _process_youtube_chat_queue(self) -> None:
        """Process messages from the YouTube chat queue in the async event loop."""
        loop = asyncio.get_event_loop()

        def get_from_queue(q: queue.Queue, timeout: float):
            """Helper function to get from queue with timeout."""
            return q.get(timeout=timeout)

        try:
            while True:
                try:
                    # Wait for message from queue (with timeout to allow checking if thread is alive)
                    try:
                        message_data = await loop.run_in_executor(
                            None, get_from_queue, self._youtube_chat_queue, 1.0
                        )
                    except queue.Empty:
                        # Check if thread is still alive
                        if (
                            self._youtube_chat_thread
                            and not self._youtube_chat_thread.is_alive()
                        ):
                            LOGGER.warning("YouTube chat thread has stopped")
                            break
                        continue

                    chatter_name = message_data["chatter_name"]
                    message = message_data["message"]
                    timestamp = message_data["timestamp"]

                    # Process the YouTube chat message (this will print the message once)
                    await self.process_chat_message(
                        chatter_name, message, platform="youtube"
                    )

                except Exception as e:
                    LOGGER.error(
                        f"Error processing YouTube chat message from queue: {e}"
                    )
                    await asyncio.sleep(1)

        except Exception as e:
            LOGGER.error(f"YouTube chat queue processing error: {e}")
        finally:
            LOGGER.info("YouTube chat queue processing stopped")

    async def _process_tts_queue(self) -> None:
        """Process TTS queue one item at a time to prevent interruptions."""
        while True:
            try:
                # Wait for a TTS request from the queue
                text = await self._tts_queue.get()
                
                # Generate TTS and get actual duration
                # This will wait for current file to finish if needed
                actual_duration = await self._generate_tts_file(text)
                
                # The file has been generated and should start playing in OBS
                # We don't need to wait here because the next TTS generation will wait
                # for this one to finish (checked in _generate_tts_file)
                # But we add a small buffer to ensure the file is detected by the overlay
                await asyncio.sleep(1.0)
                
                LOGGER.info(f"TTS generated (duration: {actual_duration:.1f}s), ready for next TTS")
                
                # Mark task as done
                self._tts_queue.task_done()
                
            except Exception as e:
                LOGGER.error(f"Error processing TTS queue: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _generate_tts_file(self, text: str) -> float:
        """Generate TTS audio file (internal method, called by queue processor).
        Waits for current file to finish playing if needed.
        Returns the duration in seconds of the generated file."""
        # Use lock to prevent concurrent TTS generation from overwriting the file
        with self._tts_lock:
            # Check if tts.mp3 exists and wait for it to finish playing
            # This is the file the overlay is actually playing from
            if os.path.exists(TTS_FILE):
                try:
                    file_age = time.time() - os.path.getmtime(TTS_FILE)
                    # Get the actual duration of the current file
                    sound = pygame.mixer.Sound(TTS_FILE)
                    current_file_duration = sound.get_length()
                    
                    # Check if file is still playing (age is less than duration + buffer)
                    if file_age < (current_file_duration + 3):
                        # File is still playing, wait for it to finish
                        remaining_time = (current_file_duration + 3) - file_age
                        if remaining_time > 0:
                            LOGGER.info(f"Current TTS still playing ({file_age:.1f}s old, {current_file_duration:.1f}s duration), waiting {remaining_time:.1f}s before generating next")
                            await asyncio.sleep(remaining_time)
                except Exception as e:
                    LOGGER.warning(f"Could not get current file duration: {e}")
            
            # Generate TTS with unique filename (timestamp-based)
            timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
            unique_filename = f"tts_{timestamp}.mp3"
            unique_filepath = unique_filename
            
            # Generate and save TTS to unique file with retry logic
            # gTTS is synchronous, so we run it in an executor
            max_retries = 3
            retry_delay = 2
            for attempt in range(max_retries):
                try:
                    # Add a small delay between retries to avoid rate limiting
                    if attempt > 0:
                        await asyncio.sleep(retry_delay * attempt)
                    
                    # Run gTTS in executor since it's synchronous
                    def generate_tts():
                        tts = gTTS(text=text, lang=bot_language, slow=False)
                        tts.save(unique_filepath)
                    
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, generate_tts)
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt == max_retries - 1:
                        # Last attempt failed, raise the error
                        LOGGER.error(f"TTS generation failed after {max_retries} attempts: {e}")
                        raise
                    else:
                        LOGGER.warning(f"TTS generation attempt {attempt + 1} failed: {e}, retrying...")
                        await asyncio.sleep(retry_delay)
            
            # Small delay to ensure file is fully written and flushed to disk
            await asyncio.sleep(0.1)
            
            # Get the actual duration
            try:
                sound = pygame.mixer.Sound(unique_filepath)
                duration_seconds = sound.get_length()
                duration_ms = int(duration_seconds * 1000)
                LOGGER.info(f"TTS file generated: {unique_filepath} (duration: {duration_ms}ms)")
            except Exception as e:
                LOGGER.warning(f"Could not get TTS duration: {e}")
                # Fallback to estimated duration
                estimated_chars = len(text)
                estimated_words = estimated_chars / 4
                estimated_duration = (estimated_words / 150) * 60
                duration_seconds = max(2.0, min(30.0, estimated_duration))
            
            # Create/update symlink or copy to main TTS_FILE for API compatibility
            # We'll use a symlink approach: create tts.mp3 as a symlink to the current file
            try:
                # Remove old symlink/file if it exists
                if os.path.exists(TTS_FILE):
                    if os.path.islink(TTS_FILE):
                        os.unlink(TTS_FILE)
                    else:
                        os.remove(TTS_FILE)
                
                # On Windows, we can't use symlinks easily, so we'll copy the file
                # But actually, let's just update the current file reference and let the API handle it
                shutil.copy2(unique_filepath, TTS_FILE)
                
                # Update current file reference
                old_file = self._current_tts_file
                self._current_tts_file = unique_filepath
                
                # Schedule cleanup of old file after it's done playing
                if old_file and os.path.exists(old_file):
                    # Clean up old file after a delay (it should be done playing by now)
                    asyncio.create_task(self._cleanup_old_tts_file(old_file, duration_seconds + 5))
                    
            except Exception as e:
                LOGGER.warning(f"Error updating TTS file reference: {e}")
            
            return duration_seconds
    
    async def _cleanup_old_tts_file(self, filepath: str, delay: float) -> None:
        """Clean up old TTS file after it's done playing."""
        await asyncio.sleep(delay)
        try:
            if os.path.exists(filepath) and filepath != TTS_FILE:
                os.remove(filepath)
                LOGGER.debug(f"Cleaned up old TTS file: {filepath}")
        except Exception as e:
            LOGGER.debug(f"Could not clean up old TTS file {filepath}: {e}")

    async def make_tts(self, text: str) -> None:
        """Queue TTS generation request."""
        # Add to queue instead of generating immediately
        if self._tts_queue is None:
            LOGGER.error("TTS queue not initialized, cannot queue TTS request")
            return
        await self._tts_queue.put(text)
        LOGGER.debug(f"TTS request queued (queue size: {self._tts_queue.qsize()})")

    def play_sound(self, file_name: str) -> None:
        """Play sound file (for overlay - file is served via Flask API)."""
        try:
            # Get duration using pygame for logging
            sound = pygame.mixer.Sound(file_name)
            duration_ms = int(sound.get_length() * 1000)

            LOGGER.info(f"TTS file generated: {file_name} (duration: {duration_ms}ms)")
            
            # Note: The overlay will play the file via the Flask API endpoint /api/tts/audio
            # We don't delete the file here - let the overlay handle playback
            # The file will be overwritten on the next TTS generation
        except Exception as e:
            LOGGER.error(f"Error processing TTS file: {e}")

    async def send_message(self, payload, message: str) -> None:
        """Send message, splitting into chunks if necessary."""
        message_len = len(message)

        if message_len > MAX_MESSAGE_LENGTH:
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message="Message is too long.",
            )
        elif message_len >= LONG_MESSAGE_THRESHOLD:
            # Split into two messages
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=message[:FIRST_MESSAGE_CHUNK],
            )
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=message[FIRST_MESSAGE_CHUNK:SECOND_MESSAGE_CHUNK],
            )
        else:
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=message,
            )

    async def send_twitch_message(self, message: str) -> None:
        """Send a message to Twitch chat."""
        try:
            # Get the channel from connected channels
            channel_name = STREAMER_NAME.lower()
            channel = self.bot.get_channel(channel_name)
            
            if channel:
                message_len = len(message)
                
                if message_len > MAX_MESSAGE_LENGTH:
                    await channel.send("Message is too long.")
                elif message_len >= LONG_MESSAGE_THRESHOLD:
                    # Split into two messages
                    await channel.send(message[:FIRST_MESSAGE_CHUNK])
                    await channel.send(message[FIRST_MESSAGE_CHUNK:SECOND_MESSAGE_CHUNK])
                else:
                    await channel.send(message)
            else:
                LOGGER.warning(f"Could not find Twitch channel: {channel_name}")
        except Exception as e:
            LOGGER.error(f"Error sending message to Twitch chat: {e}")

    async def send_youtube_message(self, message: str) -> None:
        """Send a message to YouTube live chat."""
        if not YOUTUBE_VIDEO_ID:
            return
        
        try:
            # Try to use google-api-python-client if available
            try:
                from googleapiclient.discovery import build
                from google.auth.transport.requests import Request
                import pickle
                
                # Get YouTube API credentials from environment
                youtube_live_chat_id = os.environ.get("YOUTUBE_LIVE_CHAT_ID")
                
                if not youtube_live_chat_id:
                    LOGGER.debug("YouTube live chat ID not configured, skipping YouTube message")
                    return
                
                # OAuth2 flow for YouTube API
                creds = None
                token_file = 'youtube_token.pickle'
                
                # Load existing token if available
                if os.path.exists(token_file):
                    with open(token_file, 'rb') as token:
                        creds = pickle.load(token)
                
                # If there are no (valid) credentials available, let the user log in
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        # This would require user interaction, so we'll skip for now
                        # In production, you'd want to handle OAuth flow properly
                        LOGGER.warning("YouTube OAuth token not available or expired. Please authenticate first.")
                        return
                    
                    # Save the credentials for the next run
                    with open(token_file, 'wb') as token:
                        pickle.dump(creds, token)
                
                # Build YouTube API service
                youtube = build('youtube', 'v3', credentials=creds)
                
                # Send message to live chat
                request = youtube.liveChatMessages().insert(
                    part='snippet',
                    body={
                        'snippet': {
                            'liveChatId': youtube_live_chat_id,
                            'type': 'textMessageEvent',
                            'textMessageDetails': {
                                'messageText': message
                            }
                        }
                    }
                )
                request.execute()
                LOGGER.info(f"Sent message to YouTube chat: {message}")
                
            except ImportError:
                # google-api-python-client not installed, use alternative method
                LOGGER.debug("google-api-python-client not installed, using alternative method")
                # Alternative: Use YouTube Data API v3 with direct HTTP requests
                await self._send_youtube_message_http(message)
            except Exception as e:
                LOGGER.error(f"Error sending YouTube message via API: {e}")
                # Fallback to HTTP method
                await self._send_youtube_message_http(message)
                
        except Exception as e:
            LOGGER.error(f"Error sending message to YouTube chat: {e}")

    async def _send_youtube_message_http(self, message: str) -> None:
        """Alternative method to send YouTube message using HTTP requests (requires OAuth token)."""
        youtube_access_token = os.environ.get("YOUTUBE_ACCESS_TOKEN")
        youtube_live_chat_id = os.environ.get("YOUTUBE_LIVE_CHAT_ID")
        
        if not youtube_access_token or not youtube_live_chat_id:
            LOGGER.debug("YouTube access token or live chat ID not configured")
            return
        
        try:
            url = "https://www.googleapis.com/youtube/v3/liveChat/messages"
            headers = {
                "Authorization": f"Bearer {youtube_access_token}",
                "Content-Type": "application/json"
            }
            data = {
                "snippet": {
                    "liveChatId": youtube_live_chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {
                        "messageText": message
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                LOGGER.info(f"Sent message to YouTube chat: {message}")
            else:
                LOGGER.warning(f"Failed to send YouTube message: {response.status_code} - {response.text}")
        except Exception as e:
            LOGGER.error(f"Error sending YouTube message via HTTP: {e}")


def start_bot() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    # Initialize links database on startup
    init_links_database()

    async def runner() -> None:
        async with (
            asqlite.create_pool("tokens.db") as tdb,
            Bot(token_database=tdb) as bot,
        ):
            await bot.setup_database()
            await bot.start()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt...")
