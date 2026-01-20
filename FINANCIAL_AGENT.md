# 📉 Autonomous Financial Analyst Agent

A resilient, zero-cost **Financial Intelligence Node** built for the Bindu ecosystem. This agent provides real-time stock analysis (Price, Fundamentals, News, Technique) using a novel **Zero-API-Key Architecture**.

## 🚀 Key Features

1.  **Smart Symbol Lookup**: Automatically maps company names to tickers using a 3-layer strategy:
    *   *Fast Cache*: Instant lookup for majors (Tesla $\to$ TSLA, Reliance $\to$ RELIANCE.NS).
    *   *Heuristic Match*: Identifies direct inputs (e.g., "INFY").
    *   *Deep Search*: Uses `duckduckgo-search` to resolve unknown companies (e.g., "Tata Elxsi" $\to$ "TATAELXSI.NS").
2.  **Global Market Support**: Built-in logic to handle international suffixes (like `.NS` for India) and auto-correct if data is missing.
3.  **Zero-Key Architecture**:
    *   **Data**: Sourced via `yfinance` (Community API).
    *   **Search**: Sourced via `ddgs` (Anonymous Search).
    *   **Cost**: $0.00 to operate.
4.  **Resilient Data Pipeline**: Uses full market history (`stock.history()`) instead of unreliable snapshots, ensuring perfect accuracy for Global stocks.

---

## 🛠️ Architecture

### The "3-Layer" Logic
The agent doesn't just call an API. It thinks:
1.  **Identify**: "What stock is this?" (Search Layer)
2.  **Verify**: "Do I have data?" (Validation Layer). *If no data, it auto-appends suffixes and retries.*
3.  **Analyze**: "Is it Bullish?" (computation Layer). Calculates 50-day SMA trends locally.

---

## 💻 How to Run

### 1. Install Dependencies
```bash
pip install -e .
pip install yfinance ddgs rich
```

### 2. Start the Agent
```bash
python market_agent.py
```
*Runs on port `3773`.*

### 3. Verify & Demo (Interactive)
We have included a robust verification script to demonstrate the agent's capabilities.

```bash
python verify_agent.py
```

**Try these inputs:**
*   `Tesla` (Standard US Stock)
*   `Tata Elxsi` (Indian Market - Auto-Search & Suffix Logic)
*   `Bitcoin` (Crypto support via Yahoo)

---

## 📂 Project Structure

*   **`market_agent.py`**: The Bindu Node entry point. Handles JSON-RPC protocol.
*   **`skills/market_skills.py`**: The "Brain". Contains `find_ticker`, `get_financial_summary`, and retry logic.
*   **`tests/test_market_skills.py`**: Full `pytest` suite ensuring reliability.

---

## 🏆 Why this matters
This agent solves the **"Siloed Intelligence Problem"**. Instead of relying on expensive, rate-limited APIs (Bloomberg, AlphaVantage), it constructs its own intelligence from open sources, making it a truly autonomous and sovereign node.
