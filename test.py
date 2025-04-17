from openai import OpenAI
import os
from dotenv import load_dotenv
import pyperclip
import keyboard
import time

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

messages = [
    {'role': 'user', 'content': 'from now on only give me the answer no explain'}]


def ask_openai(prompt):
    try:
        messages.append({'role': 'user', 'content': prompt})
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="gpt-4o",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


try:
    while True:
        keyboard.wait("ctrl+c")

        time.sleep(0.2)
        current_text = pyperclip.paste()

        if current_text:
            reply = ask_openai(current_text)
            pyperclip.copy(reply)

except KeyboardInterrupt:
    pass