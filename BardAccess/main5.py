import openai

openai.api_key = "YYaHTHzXhUCjQPH0yvsgT3BlbkFJUcX3sjRSmp2UMvtlXkRH"

completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[
    {"role": "user", "content": "Give me 3 ideas for apps I could build with openai apis "}])
print(completion.choices[0].message.content)
