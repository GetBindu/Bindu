import sys
from openai import OpenAI


client = OpenAI()

def explain_error(error_text: str) -> str:
    prompt = f"""
    You are a Python error explainer.
    Given this Python error:
    ```
    {error_text}
    ```
    Explain:
    1. The cause of the error
    2. How to fix it (with corrected code if needed)
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    print("Paste your Python error below, then press Enter twice:")
    lines = []
    while True:
        line = sys.stdin.readline().rstrip("\n")
        if not line:
            break
        lines.append(line)

    error_text = "\n".join(lines)
    output = explain_error(error_text)
    print("\n=== EXPLANATION ===\n")
    print(output)