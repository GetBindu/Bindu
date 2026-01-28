# 🏥 Medical Chatbot Agent (Bindu Example)

A simple healthcare advisory chatbot built using **Bindu + OpenAI gpt-oss-120b (via OpenRouter)**.

This agent answers basic health-related questions and provides safe general guidance with a disclaimer.

⚠️ Not a substitute for professional medical advice.

---

## Features

- Medical Q&A chatbot
- Powered by OpenAI gpt-oss-120b  LLM
- Runs locally as an API agent
- Easy to test with curl
- Minimal dependencies

---

## Setup

### 1. Install dependencies
pip install -r requirements.txt

### 2. Add API key

Create a `.env` file:

OPENROUTER_API_KEY=your_api_key_here

(Get key from OpenRouter dashboard)

---

## Run

python main.py

Server starts at:
http://localhost:3773

---

## Test

curl -X POST http://localhost:3773/chat -H "Content-Type: application/json" -d "{\"message\":\"I have fever and headache\"}"

---

## Example Response

{
  "reply": "You may have a viral infection. Rest and stay hydrated...",
  "disclaimer": "This is not medical advice."
}

---

## Purpose

This example demonstrates how to:

- Build an AI agent with Bindu
- Integrate an LLM
- Expose a simple API service

Useful as a starter template for healthcare or advisory bots.
