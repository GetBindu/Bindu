from examples.agent_swarm.researcher_agent import build_research_agent
from examples.agent_swarm.summarizer_agent import build_summarizer_agent
from examples.agent_swarm.critic_agent import build_critic_agent
from examples.agent_swarm.planner_agent import build_planner_agent
from examples.agent_swarm.reflection_agent import build_reflection_agent

import json
import re
import time
from typing import Any, Dict, Optional


class Orchestrator:
    def __init__(self):
        self.planner_agent = build_planner_agent()
        self.research_agent = build_research_agent()
        self.summarizer_agent = build_summarizer_agent()
        self.critic_agent = build_critic_agent()
        self.reflection_agent = build_reflection_agent()

    # ---------------- Safe JSON ----------------

    @staticmethod
    def safe_json_loads(raw: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            raw = raw.strip()

            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?", "", raw).strip()
                raw = raw.replace("```", "").strip()

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                raw = match.group()

            return json.loads(raw)

        except Exception as e:
            print("⚠️ JSON parse failed:", e)
            print("Raw output:", raw)
            return fallback or {}

    # ---------------- Fault Tolerant Agent Call ----------------

    def safe_agent_call(self, agent, input_text: str, agent_name: str, retries: int = 2) -> str:
        """
        Execute agent with retry + graceful fallback.
        """
        for attempt in range(retries + 1):
            try:
                print(f"    {agent_name} attempt {attempt + 1}")
                response = agent.run(input_text)
                return response.to_dict()["content"]

            except Exception as e:
                print(f"   ❌ {agent_name} failed:", str(e))

                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue

                print(f"   ⚠️ {agent_name} permanently failed, returning partial context.")
                return input_text

    # ---------------- Main Orchestration ----------------

    def run(self, query: str) -> str:
        MAX_SWARM_RETRIES = 2

        for swarm_attempt in range(MAX_SWARM_RETRIES + 1):
            print(f"\n🚀 Swarm Attempt {swarm_attempt + 1}")

            plan_output = self.safe_agent_call(
                self.planner_agent, query, "planner"
            )

            plan = self.safe_json_loads(plan_output, fallback={"steps": []})
            steps = plan.get("steps", [])

            if not steps:
                print("⚠️ Planner failed to generate steps")
                return "Unable to generate execution plan."

            context = query

            for idx, step in enumerate(steps, start=1):
                agent_name = step.get("agent")
                task = step.get("task", context)

                if not agent_name:
                    print(f"⚠️ Skipping invalid step: {step}")
                    continue

                print(f"\n⚡ Step {idx}: {agent_name.upper()} executing")

                if agent_name == "researcher":
                    context = self.safe_agent_call(
                        self.research_agent, task, "researcher"
                    )

                elif agent_name == "summarizer":
                    context = self.safe_agent_call(
                        self.summarizer_agent, task, "summarizer"
                    )

                elif agent_name == "critic":
                    context = self.safe_agent_call(
                        self.critic_agent, task, "critic"
                    )

                else:
                    print(f"⚠️ Unknown agent: {agent_name}")

            print("\n🧠 Reflection Phase")

            reflection_output = self.safe_agent_call(
                self.reflection_agent, context, "reflection"
            )

            feedback = self.safe_json_loads(
                reflection_output,
                fallback={"quality": "unknown", "fix_strategy": ""}
            )

            if feedback.get("quality") == "good":
                print("\n✅ Output validated by reflection agent")
                return context

            fix_strategy = feedback.get("fix_strategy", "")
            print("\n⚠️ Weak Output Detected")
            print("Fix Strategy:", fix_strategy)

            query = f"""
Improve the following answer using this strategy:

{fix_strategy}

Answer:
{context}
"""

        return context
