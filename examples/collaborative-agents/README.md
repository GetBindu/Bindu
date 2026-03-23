# 🌐 Bindu Collaborative Agents
### A Multi-Agent AI System with Semantic Memory using the Bindu Ecosystem

This project demonstrates a **collaborative AI agent system** inspired by the **Bindu Framework** and the concept of the **Internet of Agents**.

The system contains multiple agents that **communicate, collaborate, and learn over time using semantic memory**.

---

# 🚀 Features

✅ Multi-Agent Collaboration  
✅ Semantic Vector Memory  
✅ Agent Orchestration  
✅ Knowledge Retrieval with Embeddings  
✅ Dynamic Learning System  

The system demonstrates how **agents can research, store knowledge, and recall it later**.

---

# 🧠 System Architecture
```text
User Query
    ↓
Coordinator Agent
    ↓
Memory Agent (Semantic Search)
    ↓
If Found → Return Memory
If Not Found → Research Agent
    ↓
Store Knowledge
    ↓
Return Response
```


This architecture demonstrates **agent collaboration and knowledge persistence**.

---

# 🤖 Agents in the System

### 1️⃣ Coordinator Agent
Acts as the **central orchestrator**.

Responsibilities:

- Receives user queries
- Checks semantic memory
- Delegates research tasks
- Stores new knowledge

---

### 2️⃣ Research Agent
Responsible for **generating knowledge**.

Capabilities:

- Uses LLM reasoning
- Generates explanations
- Provides structured information

---

### 3️⃣ Memory Agent
Handles **semantic knowledge storage**.

Capabilities:

- Generates embeddings
- Stores vector memory
- Retrieves relevant knowledge using cosine similarity

---

# 📦 Project Structure
```bash
bindu-collaborative-agents
│
├── coordinator_agent.py
├── research_agent.py
├── memory_agent.py
├── run_system.py
│
├── utils
│   └── semantic_memory.py
│
└── requirements.txt
```

# ⚙️ Installation

### 1️⃣ Clone the repository
git clone https://github.com/Subhajitdas99/bindu-collaborative-agents.git

cd bindu-collaborative-agents


---

### 2️⃣ Install dependencies
pip install -r requirements.txt


---

### 3️⃣ Set API Key

This project uses **OpenRouter for LLM access**.
export OPENROUTER_API_KEY="your-api-key"

Windows PowerShell:
$env:OPENROUTER_API_KEY="your-api-key"


---

# ▶️ Run the System
python run_system.py


Example:
User > What is the Bindu Framework?

Coordinator thinking...

📚 Stored memory: The Bindu Framework is a platform for interoperable AI agents...

Agent > The Bindu Framework enables agents to communicate within the Internet of Agents.


---

# 🧪 Example Interaction


User > What is the Bindu Framework?

Coordinator thinking...
📚 Stored memory...

Agent > Explanation about Bindu.

User > What is Bindu again?

Coordinator thinking...
🧠 Retrieved knowledge from memory.

Agent > (From Memory) The Bindu Framework...


This demonstrates **semantic memory retrieval**.

---

# 🌍 Internet of Agents

Bindu promotes a future where AI agents:

- communicate with each other
- collaborate across systems
- exchange value
- operate autonomously

This project demonstrates a **simple prototype of that vision**.

---

# 🔧 Technologies Used

- Python
- OpenRouter API
- OpenAI Embeddings
- NumPy
- Vector Similarity Search

---

# 🎯 Use Cases

This architecture can be extended to build:

- Autonomous research agents
- Collaborative AI assistants
- Knowledge-learning AI systems
- Multi-agent decision systems

---

# 🏆 Bindu AI Agent Challenge

This project was created for the **Bindu AI Agent Competition** celebrating **International Women's Day**.

Goal:

Build an AI agent system demonstrating the **Internet of Agents**.

---

# 📚 Resources

Bindu Documentation  
https://docs.getbindu.com

Bindu GitHub  
https://github.com/GetBindu/Bindu

---

# 👨‍💻 Author

**Subhajit Das**
Final Year B.Tech AI/ML Student 
Interested in Multi-Agent Systems, AI Infrastructure, and Autonomous Agents.

---

# ⭐ Support

If you found this project interesting:

⭐ Star the repository  
🚀 Share with the AI community  

Let's build the **Internet of Agents** together.