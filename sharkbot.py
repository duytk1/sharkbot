import asyncio
import logging
import sqlite3
import os
import asqlite
import twitchio
from twitchio.ext import commands
from twitchio import eventsub
import gtts
from gtts import gTTS
import time
import pygame
import tkinter as tk
import winsound

from sharkai import SharkAI

from dotenv import load_dotenv
load_dotenv()

LOGGER: logging.Logger = logging.getLogger("Bot")

CLIENT_ID: str = os.environ.get("CLIENT_ID")
CLIENT_SECRET: str = os.environ.get("CLIENT_SECRET")
BOT_ID = os.environ.get("BOT_ID")
OWNER_ID = os.environ.get("OWNER_ID")

pob = 'https://pobb.in/SC7dZcWiNJBC'
profile = 'https://www.pathofexile.com/account/view-profile/cbera-0095/characters'


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
        # Add our component which contains our commands...
        await self.add_component(MyComponent(self))

        # Subscribe to read chat (event_message) from our channel as the bot...
        # This creates and opens a websocket to Twitch EventSub...
        subscription = eventsub.ChatMessageSubscription(
            broadcaster_user_id=OWNER_ID, user_id=BOT_ID)
        await self.subscribe_websocket(payload=subscription)

        # Subscribe and listen to when a stream goes live..
        # For this example listen to our own stream...
        subscription = eventsub.StreamOnlineSubscription(
            broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        # Make sure to call super() as it will add the tokens interally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        # Store our tokens in a simple SQLite Database when they are authorized...
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
        return resp

    async def load_tokens(self, path: str | None = None) -> None:
        # We don't need to call this manually, it is called in .login() from .start() internally...

        async with self.token_database.acquire() as connection:
            rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        for row in rows:
            await self.add_token(row["token"], row["refresh"])

    async def setup_database(self) -> None:
        # Create our token table, if it doesn't exist..
        query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
        async with self.token_database.acquire() as connection:
            await connection.execute(query)

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)


class MyComponent(commands.Component):
    def __init__(self, bot: Bot):
        # Passing args is not required...
        # We pass bot here as an example...
        self.bot = bot

    # We use a listener in our Component to display the messages received.
    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(
            f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")
        winsound.PlaySound("*", winsound.SND_ALIAS)

    @commands.command(aliases=["hello", "howdy", "hey"])
    async def hi(self, ctx: commands.Context) -> None:
        """Simple command that says hello!

        !hi, !hello, !howdy, !hey
        """
        await ctx.reply(f"Hello {ctx.chatter.mention}!")

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: commands.Context) -> None:
        """Group command for our social links.

        !socials
        """
        await ctx.send("discord.gg/..., youtube.com/..., twitch.tv/...")\
    
    @commands.group(invoke_fallback=True)
    async def ign(self, ctx: commands.Context) -> None:
        await ctx.send(f"{ctx.chatter.mention} " + "MildlyErectBaguette")

    @socials.command(name="discord")
    async def socials_discord(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.send("discord.gg/...")

    @commands.command(aliases=["repeat"])
    @commands.is_moderator()
    async def say(self, ctx: commands.Context, *, content: str) -> None:
        """Moderator only command which repeats back what you say.

        !say hello world, !repeat I am cool LUL
        """
        await ctx.send(content)

    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        # Event dispatched when a user goes live from the subscription we made above...

        # Keep in mind we are assuming this is for ourselves
        # others may not want your bot randomly sending messages...
        await payload.broadcaster.send_message(
            sender=self.bot.bot_id,
            message=f"Hi... {payload.broadcaster}! You are live!",
        )

    @commands.command(aliases=["hello", "howdy", "hey"])
    async def hi(self, ctx: commands.Context) -> None:
        """Simple command that says hello!

        !hi, !hello, !howdy, !hey
        """
        await ctx.reply(f"Hello {ctx.chatter.mention}!")

    @commands.command()
    async def ask(self, ctx: commands.Context, *, content: str) -> None:
        # if payload.broadcaster.name in payload.name or 'sharko' in payload.text:
        response = SharkAI.chat_with_openai(content)
        if len(response) > 900:
            await ctx.reply('Message is too long.')
        elif len(response) >= 500:
            await ctx.reply(f"{ctx.chatter.mention} " + response[:450])
            await ctx.reply(response[450:])
        else:
            await ctx.send(response)

        file_name = 'tts.mp3'
        self.make_tts(response, file_name)
        time.sleep(1)

        self.play_sound(file_name)

    @commands.command()
    async def pob(self, ctx: commands.Context) -> None:
        await ctx.send(pob)

    @commands.command()
    async def profile(self, ctx: commands.Context,) -> None:
        await ctx.send(profile)

    # @commands.Component.listener()
    # async def chatbot_message(self, payload: twitchio.ChatMessage) -> None:
    #     winsound.PlaySound("*", winsound.SND_ALIAS)
    #     if payload.broadcaster.name in payload.name or 'sharko' in payload.text:
    #         response = SharkAI.chat_with_openai(payload.text)
    #         if len(response) > 900:
    #             await ctx.reply('Message is too long.')
    #         elif len(response) >= 500:
    #             await ctx.reply(f"{ctx.chatter.mention} " + response[:450])
    #             await ctx.reply(response[450:])
    #         else:
    #             await ctx.send(response)

    #         file_name = 'tts.mp3'
    #         self.make_tts(response, file_name)
    #         time.sleep(1)

    #     self.play_sound(file_name)

    def make_tts(self, text, file_name):
        tts = gTTS(text=text, lang='en')
        tts.save(file_name)

    def play_sound(self, file_name):
        pygame.mixer.init()
        sound = pygame.mixer.Sound(file_name)
        duration = int(sound.get_length() * 1000)
        sound.set_volume(0.5)
        sound.play()

        root = tk.Tk()
        root.title("Sound Player")

        def close_window_and_delete_file():
            try:
                root.destroy()
                os.remove('tts.mp3')
            except FileNotFoundError:
                print("File not found.")
        root.after(duration, close_window_and_delete_file)
        root.mainloop()


def start_bot() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as tdb, Bot(token_database=tdb) as bot:
            await bot.setup_database()
            await bot.start()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt...")
