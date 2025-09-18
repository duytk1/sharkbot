import asyncio
import logging
import sqlite3
import os
import asqlite
import twitchio
from twitchio.ext import commands
from twitchio import eventsub
import pygame
import winsound
import edge_tts
import asyncio
import tkinter as tk
import database

from sharkai import SharkAI

from dotenv import load_dotenv
load_dotenv()

LOGGER: logging.Logger = logging.getLogger("Bot")

CLIENT_ID: str = os.environ.get("CLIENT_ID")
CLIENT_SECRET: str = os.environ.get("CLIENT_SECRET")
BOT_ID = os.environ.get("OWNER_ID")
OWNER_ID = os.environ.get("OWNER_ID")

pob = 'https://pobb.in/aal6ivegdR-e'
profile = 'https://www.pathofexile.com/account/view-profile/cbera-0095/characters'
ign = 'sharko_not_bait'
build = 'https://www.youtube.com/watch?v=upJPSSFeIqs'
vid = 'https://www.youtube.com/watch?v=upJPSSFeIqs'
bot_languague = 'en-AU-NatashaNeural'


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
        await self.add_component(MyComponent(self))

        subscription = eventsub.ChatMessageSubscription(
            broadcaster_user_id=OWNER_ID, user_id=BOT_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.StreamOnlineSubscription(
            broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.AdBreakBeginSubscription(
            broadcaster_user_id=OWNER_ID, moderator_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.ChannelRaidSubscription(
            to_broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.ChannelFollowSubscription(
            broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.ChannelSubscriptionGiftSubscription(
            broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.AutomodMessageHoldV2Subscription(
            broadcaster_user_id=OWNER_ID, moderator_user_id=BOT_ID)
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.ChannelBanSubscription(
            broadcaster_user_id=OWNER_ID)
        await self.subscribe_websocket(payload=subscription)
        
        subscription = eventsub.ChannelSubscribeSubscription(
            broadcaster_user_id=OWNER_ID)
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
            rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

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

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        chatter_name = payload.chatter.name
        streamer_name = payload.broadcaster.name
        message = payload.text

        conn = sqlite3.connect(os.environ.get("SQL_CONNECT"))
        cursor = conn.cursor()

        if message.split(' ', 1)[0] == 'clear' and chatter_name == 'sharko51':
            cursor.execute("DELETE FROM messages;")
            conn.commit()
            conn.close()

        if chatter_name != streamer_name:
            # Limit to 30 messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            if count >= 30:
                cursor.execute(
                    "DELETE FROM messages WHERE id = (SELECT id FROM messages ORDER BY id ASC LIMIT 1)")

            cursor.execute(
                "INSERT INTO messages (from_user, message) VALUES (?, ?)", (chatter_name, message))
            conn.commit()
            conn.close()

        print(
            f"[{chatter_name}] - {streamer_name}: {message}")
        if chatter_name != streamer_name and chatter_name != 'sharkothehuman':
            winsound.PlaySound("*", winsound.SND_ALIAS)
        if message.split(' ', 1)[0].lower() == 'sharko' or message.split(' ', 1)[0].lower() == '@sharko51':
            response = SharkAI.chat_with_openai(
                f"new message from {chatter_name}: {message}, response")
            if len(response) > 900:
                await self.send_message(payload, 'Message is too long.')
            elif len(response) >= 500:
                await self.send_message(payload, response[:490])
                await self.send_message(payload, response[491:990])
            else:
                await self.send_message(payload, response)

            tts_text = f'{chatter_name} asked me:' + \
                message.removeprefix('@sharkothehuman') + '. ' + response

            await self.make_tts(tts_text)
            self.play_sound('tts.mp3')

    @commands.group(invoke_fallback=True)
    async def ign(self, ctx: commands.Context) -> None:
        await ctx.send(f"{ctx.chatter.mention} " + ign)

    @commands.command(aliases=["repeat"])
    async def say(self, ctx: commands.Context, *, content: str) -> None:
        """
        !say {message}
        This triggers TTS bot to say the message
        """
        await self.make_tts(content)
        self.play_sound('tts.mp3')
        await ctx.send(content)

    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline) -> None:
        # Event dispatched when we go live
        await payload.broadcaster.send_message(
            sender=self.bot.bot_id,
            message=f"{payload.broadcaster} is yapping again",
        )

    @commands.Component.listener()
    async def event_ad_break(self, payload: twitchio.ChannelAdBreakBegin) -> None:
        prompt = f'an ad break has begun for {payload.duration}, thank the viewers for their patience. from then on treat the chat room as a clean new one.'
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        print('count for ad break: ' + str(count))
        if count > 0:
            prompt += ' recap the chat and mention the chatters by .'

        await self.send_message(payload, SharkAI.chat_with_openai(prompt))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages;")
        conn.commit()
        conn.close()

    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        message = SharkAI.chat_with_openai(
            f'{payload.from_broadcaster.name} is raiding, thank them')
        await self.send_message(payload, message)

    @commands.Component.listener()
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        message = SharkAI.chat_with_openai(
            f'{payload.user} followed, thank them properly')
        await self.send_message(payload, message)
        await self.make_tts(message)
        self.play_sound('tts.mp3')

    @commands.Component.listener()
    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        subscription_tier = int(payload.tier) / 1000
        message = SharkAI.chat_with_openai(
            f'{payload.user} just subscribed with tier {subscription_tier}, thank them')
        await self.send_message(payload, message)
        await self.make_tts(message)
        self.play_sound('tts.mp3')

    @commands.Component.listener()
    async def event_subscription_gift(self, payload: twitchio.ChannelSubscriptionGift) -> None:
        message = SharkAI.chat_with_openai(
            f'{payload.user} just gifted {payload.total} subs, thank them')
        await self.send_message(payload, message)
        await self.make_tts(message)
        self.play_sound('tts.mp3')

    async def event_automod_message_hold(self, payload: twitchio.AutomodMessageHold) -> None:
        winsound.PlaySound("*", winsound.SND_ALIAS)
        print('automodded message: ' + payload.text)

    async def event_ban(self, payload: twitchio.ChannelBan) -> None:
        self.send_message(payload, 'RIPBOZO')

    @commands.command(aliases=["hello", "howdy", "hey"])
    async def hi(self, ctx: commands.Context) -> None:
        """
        !hi, !hello, !howdy, !hey
        """
        message = SharkAI.chat_with_openai(f"just say hi to {ctx.chatter}")
        await ctx.reply(f'{ctx.chatter.mention} ' + message)

    @commands.command()
    async def pob(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention} ' + pob)

    @commands.command()
    async def profile(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention} ' + profile)

    @commands.command()
    async def build(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention} ' + build)
        
    @commands.command()
    async def video(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention} ' + vid)

    @commands.command()
    async def discord(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention} ' + 'https://discord.com/invite/ZyDXVXdHWM')

    @commands.command()
    async def ign(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention} ' + ign)

    @commands.command()
    async def lurk(self, ctx: commands.Context) -> None:
        message = SharkAI.chat_with_openai(
            f'{ctx.chatter.name} is lurking, tell them a joke and thank for lurking')
        await ctx.send(f'{ctx.chatter.mention} ' + message)
        
    @commands.command()
    async def mb(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention} ' + 'https://www.twitch.tv/sharko51/clip/ConsiderateProudCrabsM4xHeh-_BMzslePN11lJsY3')

    @commands.command()
    async def search(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention}' + SharkAI.search_open_ai(ctx.message))
    
    @commands.command()
    async def trick(self, ctx: commands.Context) -> None:
        await ctx.send(f'{ctx.chatter.mention}' + 'https://www.twitch.tv/sharko51/clip/ElegantPeacefulRaccoonAllenHuhu-4SNxLLMor3NV6m11')

    async def make_tts(self, text):
        tts = edge_tts.Communicate(text, bot_languague)
        await tts.save('tts.mp3')

    def play_sound(self, file_name):
        pygame.mixer.init()
        sound = pygame.mixer.Sound(file_name)
        duration = int(sound.get_length() * 1000)
        sound.set_volume(0.5)
        sound.play()

        root = tk.Tk()
        root.title("Sound Player")

        def play_and_cleanup():
            root.destroy()
            os.remove(file_name)
        root.after(duration, play_and_cleanup)
        root.mainloop()

    async def send_message(self, payload, message):
        if len(message) > 900:
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message='Message is too long.',
            )
        elif len(message) >= 500:
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=message[:480],
            )
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=message[480:990],
            )
        else:
            await payload.broadcaster.send_message(
                sender=self.bot.bot_id,
                message=message,
            )


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
