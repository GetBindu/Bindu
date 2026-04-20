def run_test():
    # Import inside the function to avoid pytest collection side effects
    try:
        from .agent import handler
    except ImportError:
        from agent import handler

    queries = [
        "What is GST?",
        "What is a contract?",
        "What is an API?"
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        try:
            response = handler([{"role": "user", "content": q}])
            print("Response:")
            print(response)
        except Exception as e:
            print(f"[ERROR] Test execution failed: {e}")


if __name__ == "__main__":
    run_test()