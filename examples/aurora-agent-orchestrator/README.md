🚀 Aurora AI — Multi-Agent Orchestration Engine

Aurora is a lightweight multi-agent orchestration engine inspired by the Internet of Agents vision by Bindu.

The system demonstrates how multiple specialized agents can register capabilities, negotiate tasks, collaborate through pipelines, and produce results autonomously.

Aurora acts as a mini orchestration layer where agents function as micro-services working together to solve complex tasks.

🌐 Core Idea

Aurora simulates an agent ecosystem where each agent specializes in a domain.

Example pipeline:

User Task
   ↓
Research Agent
   ↓
Finance Agent
   ↓
Summary Agent
   ↓
Final Output

Agents collaborate through a negotiation engine and task router to determine the best execution pipeline.

🧠 Features

• Agent Registry
• Capability-based Agent Discovery
• Reputation-weighted Negotiation Engine
• Dynamic Multi-Agent Pipeline
• Task Routing System
• Web Dashboard for Monitoring
• Task History Tracking

🏗 System Architecture
User Input
   ↓
Aurora Dashboard
   ↓
FastAPI Backend
   ↓
Task Router
   ↓
Negotiation Engine
   ↓
Collaboration Engine
   ↓
Agent Execution Pipeline
   ↓
Final Result
📂 Project Structure
aurora-bindu-engine
│
├── agents
│   ├── agent_executor.py
│   ├── finance_agent.py
│   ├── research_agent.py
│   └── summarizer_agent.py
│
├── api
│   └── routes.py
│
├── core
│   ├── collaboration_engine.py
│   ├── negotiation_engine.py
│   └── task_router.py
│
├── dashboard
│   └── index.html
│
├── database
│   └── db.py
│
├── models
│   ├── agent_model.py
│   └── task_model.py
│
├── tests
│
├── main.py
├── requirements.txt
└── README.md
⚙️ Tech Stack

Python
FastAPI
HTML / CSS Dashboard
Multi-Agent Orchestration Engine

📦 Installation

Clone the repository:

git clone https://github.com/<your-username>/aurora-bindu-engine.git
cd aurora-bindu-engine

Install dependencies:

pip install -r requirements.txt
▶️ Running the Server

Start the FastAPI server:

uvicorn main:app --reload

Server will run at:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs
🤖 Register Example Agents

Before executing tasks, register agents using the API.

Open:

http://127.0.0.1:8000/docs
Register Research Agent

POST /register_agent

{
 "agent_id": "research_agent",
 "capability": "research",
 "reputation": 6
}
Register Finance Agent

POST /register_agent

{
 "agent_id": "finance_agent",
 "capability": "finance",
 "reputation": 9.5
}
Register Summary Agent

POST /register_agent

{
 "agent_id": "summary_agent",
 "capability": "summary",
 "reputation": 7
}
🖥 Running the Dashboard

Open the dashboard:

dashboard/index.html

The dashboard allows you to:

• Run tasks
• View registered agents
• Monitor execution pipelines
• Track task history
• Check system status

🧪 Example Task

Input:

research and finance analysis of tesla earnings

Pipeline Generated:

research_agent → finance_agent → summary_agent

Output:

Summary: Tesla earnings indicate positive financial performance.