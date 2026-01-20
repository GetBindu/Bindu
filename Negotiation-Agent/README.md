# Negotiation Agent (NegotiBot AI)

## Project Description
NegotiBot AI is a comprehensive, AI-powered marketplace negotiation platform designed to autonomously negotiate product prices on behalf of users. It leverages advanced Large Language Models (LLMs) to interact with sellers on platforms like OLX and Quikr, employing strategic negotiation tactics to secure the best possible deals. The system combines robust web scraping capabilities with a sophisticated decision-making engine to automate the entire buying process, from product discovery to final price agreement.

---

## Project Details

### Problem Statement
Online marketplaces offer great deals, but the process of finding the right product, contacting multiple sellers, and negotiating prices is time-consuming and often requires significant effort. NegotiBot AI solves this by automating the discovery and negotiation phases, ensuring users get fair prices without the hassle of manual messaging.

### Key Features
*   **Autonomous Negotiation:** Uses LangChain and Gemini/OpenAI to simulate human-like negotiation behaviors.
*   **Smart Scraping:** Integrated scrapers (Playwright/Selenium) for fetching real-time listings from platforms like OLX and Quikr.
*   **Adaptive Tactics:** Implements proven negotiation strategies such as Anchoring, Scarcity, Urgency, and Reciprocity.
*   **Real-time Communication:** WebSocket-based architecture for seamless, real-time updates and interaction.
*   **Dual-Interface:** 
    *   **Buyer Portal:** For users to search products and monitor negotiations.
    *   **Seller Portal:** For simulating seller responses and testing agent behavior.

### Negotiation Engine
The core engine supports dynamic strategy adjustment based on:
*   **Market Analysis:** Compares prices with similar listings (`Market Analysis Enabled`).
*   **Sentiment Analysis:** Gauges seller responses to adjust tone and aggressiveness.
*   **Confidence Thresholds:** Determines when to accept an offer or walk away.

---

## Tech Stack

### Backend
*   **Framework:** FastAPI (Python)
*   **AI/ML:** LangChain, Google Gemini Pro, OpenAI GPT
*   **Scraping:** Playwright, Selenium, Beautiful Soup
*   **Real-time:** WebSockets
*   **Data:** Pydantic, Pandas

### Frontend
*   **Framework:** React (Vite)
*   **Styling:** Tailwind CSS, Framer Motion
*   **State Management:** Zustand
*   **UI Components:** Headless UI, Lucide React

### Infrastructure & Tools
*   **Protocol:** Model Context Protocol (MCP)
*   **Environment:** Python dotenv
*   **Linting:** ESLint

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/Abinesh2418/AI-Negotiation-Agent.git
cd AI-Negotiation-Agent
```

### 2. Backend Setup
Navigate to the backend directory and install dependencies:
```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```
Create a `.env` file based on `.env.example` and configure your API keys (Gemini/OpenAI).

Run the server:
```bash
uvicorn main:app --reload
```

### 3. Frontend Setup
Open a new terminal, navigate to the frontend directory, and start the React app:
```bash
cd frontend
npm install
npm run dev
```

---

## Usage
1.  **Launch the Application:** Access the frontend (typically `http://localhost:5173`) and the backend API (`http://localhost:8001/docs`).
2.  **Start a Negotiation:** Enter a product search term (e.g., "iPhone 13") and platform preferences.
3.  **Monitor Progress:** Watch the agent scrape listings and initiate conversations with sellers in the dashboard.
4.  **Review Deals:** detailed logs of the negotiation rounds and final agreed prices.

---

## Project Structure
```
AI-Negotiation-Agent/
├── backend/                     # Backend Application
│   ├── data/                    # Backend data storage
│   │   ├── auth_sessions.json   # Authentication session data
│   │   └── users.json           # User database
│   ├── auth_service.py          # Authentication logic and user management
│   ├── database.py              # Database connection and session handling
│   ├── enhanced_ai_service.py   # Advanced AI processing capabilities
│   ├── enhanced_scraper.py      # Improved scraping for product listings
│   ├── gemini_service.py        # Integration with Google Gemini AI
│   ├── langchain_agent.py       # LangChain-based negotiation agent
│   ├── main.py                  # FastAPI application entry point
│   ├── mcp_integration.py       # Model Context Protocol integration
│   ├── models.py                # Pydantic data models and schemas
│   ├── negotiation_engine.py    # Core negotiation logic and strategy
│   ├── scraper_service.py       # Base scraping service modules
│   ├── session_manager.py       # Manages user sessions and states
│   └── websocket_manager.py     # Handles real-time WebSocket connections
│
├── data/                        # General data directory
│   ├── auth_sessions.json       # Global authentication sessions
│   ├── products.json            # Product listings and information
│   ├── sessions.json            # Negotiation session data
│   └── users.json               # User accounts database
│
├── frontend/                    # Frontend Application
│   ├── src/                     # React source code directory
│   │   ├── components/          # Reusable UI components
│   │   │   ├── ChatInterface.jsx           # Main chat interface component
│   │   │   ├── ChatInterfaceFixed.jsx      # Fixed version of chat interface
│   │   │   ├── ChatInterfaceNew.jsx        # New chat interface implementation
│   │   │   ├── MarketAnalysis.jsx          # Market analysis display
│   │   │   ├── MessageBubble.jsx           # Chat message bubble component
│   │   │   ├── ProductCard.jsx             # Product listing card
│   │   │   ├── SellerPortal.jsx            # Seller portal interface
│   │   │   ├── SellerPortalBackup.jsx      # Backup seller portal
│   │   │   ├── Sidebar.jsx                 # Navigation sidebar
│   │   │   ├── SidebarNew.jsx              # Updated sidebar component
│   │   │   └── UnifiedAuth.jsx             # Authentication component
│   │   ├── hooks/               # Custom React hooks
│   │   │   └── useNegotiationStore.js      # Negotiation state management
│   │   ├── services/            # External service integrations
│   │   │   ├── api.js           # API service layer
│   │   │   └── websocket.js     # WebSocket service layer
│   │   ├── App.jsx              # Main application component
│   │   ├── AppSelfContained.jsx # Self-contained app version
│   │   ├── AppSelfContainedImproved.jsx # Improved self-contained version
│   │   ├── index.css            # Global styles
│   │   └── main.jsx             # React application entry point
│   ├── index.html               # Main application HTML
│   ├── package.json             # Project dependencies and scripts
│   ├── postcss.config.js        # PostCSS configuration
│   ├── react-app.html           # React application template
│   ├── seller-portal.html       # Dedicated interface for sellers
│   ├── tailwind.config.js       # Tailwind CSS configuration
│   └── vite.config.js           # Vite build tool configuration
│
├── .env.example                 # Template for environment variables
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python project dependencies
└── README.md                    # Project documentation
```

---

## Contributing

Contributions are welcome! To contribute:
1. Fork the repository
2. Create a new branch:
   ```bash
   git checkout -b feature/your-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add your feature"
   ```
4. Push to your branch:
   ```bash
   git push origin feature/your-feature
   ```
5. Open a pull request describing your changes.

---

## 📬 Contact
For any queries or suggestions, feel free to reach out:

- 📧 **Email:** abineshbalasubramaniyam@gmail.com
- 💼 **LinkedIn:** [linkedin.com/in/abinesh-b-1b14a1290/](https://linkedin.com/in/abinesh-b-1b14a1290/)
- 🐙 **GitHub:** [github.com/Abinesh2418](https://github.com/Abinesh2418)
- 💻 **LeetCode:** [leetcode.com/u/abinesh_06/](https://leetcode.com/u/abinesh_06/)
