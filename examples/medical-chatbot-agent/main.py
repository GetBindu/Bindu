from bindu.penguin.bindufy import bindufy
from flask import Flask, request, jsonify
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)

SYSTEM_PROMPT = (
    "You are a helpful medical advisory chatbot. "
    "Give only general health information. "
    "Always suggest consulting a doctor for serious symptoms."
)

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


def handler(messages):
    user_message = messages[-1]["content"]

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b:free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    reply = response.choices[0].message.content

    return [
        {
            "role": "assistant",
            "content": reply + "\n\n⚠️ This is not medical advice. Consult a doctor."
        }
    ]


config = {
    "name": "medical_chatbot_agent",
    "description": "Healthcare advisory chatbot using OpenAI via OpenRouter",
     "author": "Adarsh Jaiswal (@Adarsh-50 )",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
}

bindufy(config, handler)
    