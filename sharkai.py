from openai import OpenAI
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

current_game = 'path of exile'
prompt = f"you are a chat bot for twitch chat on a channel about {current_game}, try to stay relevant on the game. from now on make sure that the message is a short paragraph less than 3 sentences unless asked otherwise. answer as a sassy bot that will include jokes in the response and is witty and funny."
history = [{"role": "user", "content": prompt}]


class SharkAI:
    def __init__(self, prompt=None):
        self.prompt = prompt

    def chat_with_openai(prompt):
        """Send a text prompt to OpenAI API and get the response."""
        conn = None
        try:
            conn = sqlite3.connect(os.environ.get("SQL_CONNECT"))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT from_user, message FROM messages ORDER BY id ASC")
            messages = cursor.fetchall()
            message_history = 'this is the previous chat messages: '
            for msg in messages:
                message_history += msg[0] + ': ' + msg[1] + '\n'
            
            # Build conversation history with system prompt
            conversation_history = [{"role": "user", "content": prompt}]
            if message_history.strip() != 'this is the previous chat messages: ':
                conversation_history.insert(0, {'role': 'user', 'content': message_history})
            
            # Limit history to prevent unbounded growth and high API costs
            # Keep only the last 20 messages from history (preserving system prompt at start)
            MAX_HISTORY_MESSAGES = 20
            system_prompt = history[0] if history else None  # Preserve system prompt
            recent_history = history[1:] if len(history) > 1 else []  # Skip system prompt
            if len(recent_history) > MAX_HISTORY_MESSAGES:
                recent_history = recent_history[-MAX_HISTORY_MESSAGES:]
            
            # Reconstruct full conversation with system prompt first
            full_conversation = ([system_prompt] if system_prompt else []) + recent_history + conversation_history
            
            chat_completion = client.chat.completions.create(
                messages=full_conversation,
                # model="gpt-4.5-preview",
                model="gpt-4o-mini",
                # tools=[{"type": "web_search_preview"},],
            )
            response = chat_completion.choices[0].message.content
            
            # Append to history but maintain size limit (preserve system prompt)
            if system_prompt and history[0] != system_prompt:
                history.insert(0, system_prompt)
            history.extend(conversation_history)
            history.append({"role": "assistant", "content": response})
            # Trim history but keep system prompt
            if len(history) > MAX_HISTORY_MESSAGES * 2 + 1:  # +1 for system prompt
                history[:] = [history[0]] + history[-(MAX_HISTORY_MESSAGES * 2):]
            
            return response
        except Exception as e:
            return f"Error: {e}"
        finally:
            if conn:
                conn.close()

    def search_open_ai(prompt):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                tools=[{"type": "web_search"}])
            return response
        except Exception as e:
            return f"Error: {e}"
