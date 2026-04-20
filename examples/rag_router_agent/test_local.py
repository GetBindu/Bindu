from agent import handler


if __name__ == "__main__":
    messages = [
        {"role": "user", "content": "What is GST?"}
    ]

    response = handler(messages)
    print(response)