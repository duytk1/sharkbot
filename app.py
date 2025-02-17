from sharkai import SharkAI

if __name__ == "__main__":
    user_input = input("Enter your text: ")
    response = SharkAI.chat_with_openai(user_input)
    print(response)
