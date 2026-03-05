from researcher_agent import build_research_agent
from summarizer_agent import build_summarizer_agent
from critic_agent import build_critic_agent
from planner_agent import build_planner_agent
from reflection_agent import build_reflection_agent

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

    @staticmethod
    def safe_json_loads(
        raw: str, fallback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            raw = raw.strip()

            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?", "", raw).strip()
                raw = raw.replace("```", "").strip()

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                raw = match.group()

            parsed = json.loads(raw)
            print(f"✅ JSON parsed successfully: {parsed}")
            return parsed

        except Exception as e:
            print("⚠️ JSON parse failed:", e)
            print("Raw output (first 200 chars):", raw[:200])
            return fallback or {}

    @staticmethod
    def _extract_final_content(critic_output: str) -> str:
        """
        Extract only the final polished version from critic output,
        removing any evaluation or analysis sections.
        """
        markers = [
            "Polished, Professional Final Version:",
            "Enhanced Version:",
            "Improved Version:",
            "Final Version:",
            "Refined Version:",
            "Corrected Version:",
            "Updated Version:",
        ]

        for marker in markers:
            if marker in critic_output:
                parts = critic_output.split(marker, 1)
                if len(parts) > 1:
                    return parts[1].strip()

        lines = critic_output.split("\n")

        skip_keywords = [
            "evaluation",
            "criticism",
            "critique",
            "weakness",
            "analysis",
            "improvement:",
            "constructive",
            "here's a",
            "here is a",
            "refined version",
            "suggested changes",
            "issues found",
        ]

        content_start = 0
        for i, line in enumerate(lines):
            lower_line = line.lower().strip()

            if not lower_line:
                continue

            is_meta = any(keyword in lower_line for keyword in skip_keywords)

            if is_meta:
                content_start = i + 1
            else:
                break

        final_content = "\n".join(lines[content_start:]).strip()

        return final_content if final_content else critic_output

    def safe_agent_call(
        self, agent, input_text: str, agent_name: str, retries: int = 2
    ) -> str:
        """
        Execute agent with retry + graceful fallback.
        """
        for attempt in range(retries + 1):
            try:
                print(f"    {agent_name} attempt {attempt + 1}")
                response = agent.run(input_text)
                content = response.to_dict()["content"]

                snippet = content[:150] + "..." if len(content) > 150 else content
                print(f"    ✅ {agent_name} completed: {snippet}")

                return content

            except Exception as e:
                print(f"   ❌ {agent_name} failed:", str(e))

                if attempt < retries:
                    wait_time = 1.5 * (attempt + 1)
                    print(f"   ⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                print(
                    f"   ⚠️ {agent_name} permanently failed, returning partial context."
                )
                return input_text

    def run(self, query: str) -> str:
        MAX_SWARM_RETRIES = 2

        for swarm_attempt in range(MAX_SWARM_RETRIES + 1):
            print(f"\n{'=' * 60}")
            print(f"🚀 Swarm Attempt {swarm_attempt + 1}/{MAX_SWARM_RETRIES + 1}")
            print(f"{'=' * 60}")

            plan_output = self.safe_agent_call(self.planner_agent, query, "planner")

            plan = self.safe_json_loads(plan_output, fallback={"steps": []})
            steps = plan.get("steps", [])

            if not steps:
                print("⚠️ Planner failed to generate steps")
                if swarm_attempt < MAX_SWARM_RETRIES:
                    print("   Retrying swarm...")
                    continue
                return "Unable to generate execution plan after multiple attempts."

            print(f"\n📋 Execution Plan: {len(steps)} steps")
            for i, step in enumerate(steps, 1):
                print(
                    f"   {i}. {step.get('agent', 'unknown').upper()}: {step.get('task', 'N/A')[:80]}..."
                )

            context = query

            for idx, step in enumerate(steps, start=1):
                agent_name = step.get("agent")
                task_instruction = step.get("task", "")

                if not agent_name:
                    print(f"\n⚠️ Skipping invalid step: {step}")
                    continue

                print(f"\n{'─' * 60}")
                print(f"⚡ Step {idx}/{len(steps)}: {agent_name.upper()}")
                print(f"{'─' * 60}")

                if idx == 1:
                    agent_input = f"{task_instruction}\n\nQuery: {query}"
                else:
                    agent_input = f"{task_instruction}\n\nPrevious output to work with:\n{context}"

                if agent_name == "researcher":
                    context = self.safe_agent_call(
                        self.research_agent, agent_input, "researcher"
                    )

                elif agent_name == "summarizer":
                    context = self.safe_agent_call(
                        self.summarizer_agent, agent_input, "summarizer"
                    )

                elif agent_name == "critic":
                    raw_critic_output = self.safe_agent_call(
                        self.critic_agent, agent_input, "critic"
                    )
                    context = self._extract_final_content(raw_critic_output)
                    print(
                        f"    🧹 Cleaned critic output (first 150 chars): {context[:150]}..."
                    )

                else:
                    print(f"⚠️ Unknown agent: {agent_name}")
                    continue

            print(f"\n{'─' * 60}")
            print("🧠 Reflection Phase")
            print(f"{'─' * 60}")

            reflection_output = self.safe_agent_call(
                self.reflection_agent, context, "reflection"
            )

            feedback = self.safe_json_loads(
                reflection_output, fallback={"quality": "unknown", "fix_strategy": ""}
            )

            quality = feedback.get("quality", "unknown")
            issues = feedback.get("issues", [])
            fix_strategy = feedback.get("fix_strategy", "")

            print(f"\n📊 Quality Assessment: {quality.upper()}")
            if issues:
                print(f"⚠️ Issues found: {', '.join(issues)}")

            if quality == "good":
                print("\n" + "=" * 60)
                print("✅ Output validated by reflection agent - SUCCESS!")
                print("=" * 60)
                return context

            print("\n⚠️ Output needs improvement")
            if fix_strategy:
                print(f"🔧 Fix Strategy: {fix_strategy}")

            if swarm_attempt < MAX_SWARM_RETRIES:
                print(
                    f"\n🔄 Preparing retry {swarm_attempt + 2}/{MAX_SWARM_RETRIES + 1}..."
                )
                query = f"""
Improve the following answer using this strategy:

{fix_strategy}

Answer:
{context}
"""
            else:
                print("\n⚠️ Max retries reached - returning best available output")

        print("\n" + "=" * 60)
        print("⚠️ Swarm completed with warnings - returning final context")
        print("=" * 60)
        return context
