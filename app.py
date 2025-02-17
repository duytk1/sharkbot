from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set your OpenAI API key
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def chat_with_openai(prompt):
    """Send a text prompt to OpenAI API and get the response."""
    try:
        # response = openai.chat.completions.create(
        #     model="gpt-3.5-turbo",  # You can use "gpt-3.5-turbo" for a cheaper option
        #     messages=[{"role": "user", "content": prompt}],
        #     temperature=0.7,
        # )
        # return response["choices"][0]["message"]["content"]
        pre_prompt = "write as a short paragraph less than 50 words "
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": pre_prompt + prompt,
                }
            ],
            # model="gpt-3.5-turbo",
            model="gpt-4o-mini"
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    user_input = input("Enter your text: ")
    response = chat_with_openai(user_input)
    print(response)
