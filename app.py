import asyncio
import threading

from sharkbot import start_bot


def run_bot():
    asyncio.run(start_bot())


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    while True:
        # user_input = input("Enter your text: ")
        # if user_input.lower() == "exit":
        #     print("Shutting down bot...")
        #     break

        # response = SharkAI.chat_with_openai(user_input)
        # print(response)
        pass
