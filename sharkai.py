from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

history = []


class SharkAI:
    def __init__(self, prompt=None):
        self.prompt = prompt

    def chat_with_openai(prompt):
        """Send a text prompt to OpenAI API and get the response."""
        try:
            history.append({"role": "user", "content": prompt})
            chat_completion = client.chat.completions.create(
                messages=history,
                model="gpt-4o-mini",
            )
            print('fff', history)
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"
