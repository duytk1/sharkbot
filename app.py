import openai
from twitchio.ext import commands

# Set up OpenAI API key
openai.api_key = 'your_openai_api_key'

# Set up Twitch bot credentials
TMI_TOKEN = 'oauth:your_oauth_token'  # You can get this from https://twitchtokengenerator.com/
CLIENT_ID = 'your_client_id'
CHANNEL = 'your_twitch_channel_name'

# Define the bot
bot = commands.Bot(
    irc_token=TMI_TOKEN,
    client_id=CLIENT_ID,
    prefix='!',
    initial_channels=[CHANNEL]
)

# Function to get ChatGPT response
async def get_chatgpt_response(prompt: str):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error: {e}")
        return "Sorry, something went wrong!"

# Event: When the bot is ready
@bot.event
async def event_ready():
    print(f'Logged in as | {bot.nick}')

# Event: When a message is received in the chat
@bot.event
async def event_message(message):
    if message.author.name.lower() == bot.nick.lower():
        return  # Ignore messages from the bot

    # Get a response from ChatGPT
    chatgpt_response = await get_chatgpt_response(message.content)

    # Send the response to the Twitch chat
    await message.channel.send(chatgpt_response)

# Run the bot
if __name__ == "__main__":
    bot.run()
