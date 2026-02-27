# LangGraph Blog Writing Agent

A fully autonomous AI agent designed to research, plan, and write comprehensive technical blog posts. This project uses **LangGraph** to implement a "Map-Reduce" architecture for parallel content generation and **Bindu** for deployment.

## 🚀 Overview

Unlike simple linear chains, this agent uses a **Map-Reduce** pattern to generate long-form content:
1.  **Orchestrator:** BREAKS the topic down into a detailed `Plan` with specific tasks (sections), word counts, and bullet points.
2.  **Fanout:** DISTRIBUTES these tasks to parallel workers.
3.  **Workers:** WRITE each section simultaneously, ensuring specific technical depth and adherence to constraints.
4.  **Reducer:** AGGREGATES the sections into a final, cohesive markdown article.

## 📂 Project Structure

* `main.py`: The entry point script. Handles the API interface using `bindufy`.
* `graph.py`: Contains the core logic: `Task` models, the Orchestrator, Worker, and Reducer nodes.
* `schemas.py`: Defines the API response format (`AgentResponse`).

## 🛠️ Prerequisites

* Python 3.9+
* `bindu-penguin`
* `langgraph`
* `langchain` & `langchain-openai`
* `pydantic`

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd langgraph_blog_writing_agent
    ```

2.  **Install dependencies:**
    ```bash
    pip install langgraph langchain langchain-openai pydantic python-dotenv bindu-penguin
    ```

3.  **Environment Variables:**
    Create a `.env` file in the root directory. You must provide an OpenAI API key.
    *(Note: The code is configured to use `gpt-5.2`. If you do not have access to this model, update the code to use `gpt-4o` or `gpt-4-turbo`)*.
    ```bash
    OPENAI_API_KEY=sk-...
    ```

## 🏃‍♂️ Usage

To start the agent server, run the entry script:

```bash
uv run main.py