import openai

# Set your OpenAI API key
api_key = 'YYaHTHzXhUCjQPH0yvsgT3BlbkFJUcX3sjRSmp2UMvtlXkRH'
openai.api_key = api_key

# Define the conversation prompt
prompt_text = "The following is a conversation with a ChatGPT AI:\n\nUser: Hello, how are you?\nAI:"

while True:
    user_input = input("You: ")  # Get user input

    # Create the prompt by combining user input with AI's response
    prompt_text += f"\nUser: {user_input}\nAI:"

    # Send the prompt to the GPT model
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": user_input}
        ]
    )

    # Get the AI's response from the completion
    ai_response = response['choices'][0]['message']['content']
    print(f"AI: {ai_response}")
    prompt_text += f" {ai_response}\nUser:"
