# Financial Analyst Agent - Walkthrough

You have successfully built a **Financial Intelligence Node** for the Bindu ecosystem.

## 🚀 Capabilities
*   **Smart Lookup**: Understands "Tesla" -> `TSLA`, "Reliance" -> `RELIANCE.NS`.
*   **Live Market Data**: Real-time Price, Change %, and Volume.
*   **Fundamental Analysis**: P/E Ratio, Market Cap.
*   **Technical Pulse**: Trend detection (Bullish/Bearish).
*   **News Sentiment**: Latest headlines.

## 🔑 Why No API Keys? (Interview Talking Point)
You might notice this project requires **Zero API Keys**. This is a deliberate "Open Architecture" choice:

*   **Data**: Uses `yfinance`, which leverages public Yahoo Finance endpoints (community standard for Python/ML).
*   **Search**: Uses `duckduckgo-search` for anonymous, key-free web resolving.
*   **Benefit**: This creates a **Censorship-Resistant & Zero-Cost** node that anyone can deploy immediately without barriers.

## 🛠️ How to Run

### 1. Start the Agent
Open a terminal and run:

```bash
python market_agent.py
```
The agent will start on `http://localhost:3773`.

### 2. Test the Agent
Open a new terminal and run the interactive console:

```bash
python verify_agent.py
```
This will launch a Test Console where you can type any stock name:

*   `Tata Elxsi` (Auto-resolves to `TATAELXSI.NS`)
*   `Tesla` (Resolves to `TSLA`)
*   `Reliance` (Resolves to `RELIANCE.NS`)

The script handles the complex JSON-RPC communication for you.

## 🛡️ Robustness Features
*   **Smart Search**: Uses DuckDuckGo to find tickers for unknown companies.
*   **Auto-Retry**: If a ticker is found but has no data, it automatically appends suffix codes (like `.NS`) and retries.
*   **History-First**: Uses full market history data instead of unreliable snapshot APIs.

## 📂 Project Structure
*   `market_agent.py`: Main agent service (The Node).
*   `skills/market_skills.py`: The logic (The Brain).
*   `skills/market_skill.yaml`: Capability definition (The ID Card).
