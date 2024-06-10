import openai

# Set your OpenAI API key
api_key = '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'
openai.api_key = api_key

# Initial conversation prompt
prompt_text = "The following is a conversation with a ChatGPT AI:\n\nUser: Hello, how are you?\nAI:"

while True:
    user_input = input("You: ")  # Get user input

    # Create the prompt by combining user input with AI's response
    prompt_text += f"\nUser: {user_input}\nAI:"

    # Send the prompt to the GPT model
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt_text,
        max_tokens=50  # Set the desired maximum number of tokens for the completion
    )

    # Get the AI's response from the completion
    ai_response = response.choices[0].text.strip()
    print(f"AI: {ai_response}")
    prompt_text += f" {ai_response}\nUser:"
