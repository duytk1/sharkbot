from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


class SharkAI:
    def __init__(self, prompt):
        self.prompt = prompt

    def chat_with_openai(prompt):
        """Send a text prompt to OpenAI API and get the response."""
        try:
            word_count = 50
            pre_prompt = "write as a short paragraph less than " + \
                str(word_count) + " words "
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": pre_prompt + prompt,
                    }
                ],
                # model="gpt-3.5-turbo",
                model="gpt-4o-mini",
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"
