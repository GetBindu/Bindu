from flask import Flask, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

app = Flask(__name__)

SYSTEM_PROMPT = (
    "You are a helpful medical advisory chatbot. "
    "Give only general health information. "
    "Always suggest consulting a doctor for serious symptoms. "
)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )

    reply = response.choices[0].message.content

    return jsonify({
        "reply": reply,
        "disclaimer": "This is not medical advice."
    })


if __name__ == "__main__":
    print("Running at http://localhost:3773")
    app.run(port=3773)
