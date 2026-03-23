import os
import traceback
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# Custom Data Analyst Tools
# -----------------------------

def analyze_dataset(file_path: str) -> str:
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}. Please provide a valid absolute path."
    try:
        df = pd.read_csv(file_path)
        info = [
            f"Dataset Shape: {df.shape[0]} rows, {df.shape[1]} columns\n",
            "Columns and Data Types:\n" + str(df.dtypes) + "\n",
            "Missing Values:\n" + str(df.isnull().sum()) + "\n",
            "Summary Statistics:\n" + df.describe(include='all').to_string()
        ]
        return "\n".join(info)
    except Exception as e:
        return f"Error analyzing dataset: {str(e)}"

def generate_visualization(file_path: str, x_column: str, y_column: str, chart_type: str = "bar") -> str:
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}."
    try:
        df = pd.read_csv(file_path)
        if x_column not in df.columns or (y_column and y_column not in df.columns):
            return f"Error: Columns '{x_column}' or '{y_column}' not found."

        plt.figure(figsize=(10, 6))
        sns.set_theme(style="whitegrid")

        if chart_type == "bar":
            sns.barplot(data=df, x=x_column, y=y_column)
        elif chart_type == "line":
            sns.lineplot(data=df, x=x_column, y=y_column)
        else:
            sns.scatterplot(data=df, x=x_column, y=y_column)

        plt.title(f"{chart_type.capitalize()} Chart: {y_column} vs {x_column}")
        plt.xticks(rotation=45)
        plt.tight_layout()

        os.makedirs("outputs", exist_ok=True)
        output_path = f"outputs/chart_{x_column}_{y_column}.png"
        plt.savefig(output_path)
        plt.close()

        return f"Success! Visualization generated and saved to: {output_path}"
    except Exception as e:
        return f"Error generating visualization: {str(e)}"

# -----------------------------
# Agent Handler
# -----------------------------

def handler(messages: list[dict]):
    print("\n[DEBUG] --- Handler Triggered! ---")

    try:
        last_message = messages[-1]
        user_query = ""

        # Safely extract text from the Bindu payload
        if "parts" in last_message:
            for part in last_message["parts"]:
                if part.get("kind") == "text":
                    user_query += part.get("text", "") + "\n"
        elif "content" in last_message:
            user_query = last_message.get("content", "")

        user_query = user_query.strip()
        print(f"[DEBUG] Extracted query: {user_query}")

        if not user_query:
            return [{"role": "assistant", "content": "Error: No text received."}]

        # Instantiate agent cleanly inside the thread
        agent = Agent(
            name="AI Data Analysis Agent",
            instructions=[
                "You are an elite Data Scientist.",
                "When a user provides a path to a CSV, use the 'analyze_dataset' tool to understand its structure.",
                "Proactively use the 'generate_visualization' tool to create compelling charts.",
                "Always format your final output as a highly structured analytical report using Markdown."
            ],
            model=OpenRouter(
                id="openai/gpt-oss-120b",
                api_key=os.getenv("OPENROUTER_API_KEY"),), # Or whatever model you prefer!
            tools=[analyze_dataset, generate_visualization],
            markdown=True,
            telemetry=False # Keep this to prevent Agno from fighting with Bindu's tracing
        )

        print("[DEBUG] Agent is analyzing the data...")
        result = agent.run(user_query)
        print("[DEBUG] Analysis complete!")

        # Agent autonomously saves its own report
        os.makedirs("outputs", exist_ok=True)
        report_path = "outputs/analysis_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(result.content)
        print(f"[DEBUG] Saved Markdown report to {report_path}")

        return [{"role": "assistant", "content": str(result.content)}]

    except Exception as e:
        print(f"\n[REAL ERROR CAUGHT]: {str(e)}")
        traceback.print_exc()
        return [{"role": "assistant", "content": f"Agent crashed: {str(e)}"}]

# -----------------------------
# Bindu Configuration
# -----------------------------

config = {
    "author": "your.email@example.com",
    "name": "AI Data Analysis Agent",
    "description": "An analytical agent that processes CSV data and generates visual charts.",
    "deployment": {
            "url": "http://localhost:3773",
            "expose": True,
            "cors_origins": ["http://localhost:5173"]
        },
    "skills":["skills/ai-data-analysis-agent"],
}

if __name__ == "__main__":
    bindufy(config=config, handler=handler)
