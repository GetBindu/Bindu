from agent import handler


def run_test():
    messages = [
        {"role": "user", "content": "What is GST?"}
    ]

    try:
        response = handler(messages)
        print("Response:")
        print(response)
    except Exception as e:
        print(f"[ERROR] Test execution failed: {e}")


if __name__ == "__main__":
    run_test()