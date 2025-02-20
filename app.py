import asyncio
import threading

from sharkai import SharkAI
from sharkbot import start_bot


def run_bot():
    asyncio.run(start_bot())


# Start the bot in a background thread
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == "__main__":
    while True:
        # user_input = input("Enter your text: ")
        # if user_input.lower() == "exit":
        #     print("Shutting down bot...")
        #     break

        # response = SharkAI.chat_with_openai(user_input)
        # print(response)
        pass
