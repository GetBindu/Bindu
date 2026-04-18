from agent import handler

messages = [
    {"role": "user", "content": "What is GST?"}
]

response = handler(messages)

print(response)
