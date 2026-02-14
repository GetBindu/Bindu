"""
Individual Agent Implementations
Each agent has a specific role in the CBT exercise generation process.
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
import json
from pathlib import Path
from dotenv import load_dotenv

from state import ProtocolState
from utils import log_agent_activity

# Load environment variables from .env file in cbt folder
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_llm():
    """Get the LLM instance using OpenAI API"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not found. Get your key from https://openrouter.ai/keys"
        )

    base_url = "https://openrouter.ai/api/v1"

    # Using OpenRouter's GPT model
    model_name = "openai/gpt-oss-120b"
    return ChatOpenAI(
        api_key=api_key, base_url=base_url, model=model_name, temperature=0.7
    )


class DrafterAgent:
    """Creates initial CBT exercise drafts based on user intent"""

    def __init__(self, llm=None):
        self.llm = llm or get_llm()
        self.name = "Drafter"

    async def draft(self, state: ProtocolState) -> Dict[str, Any]:
        """Generate an initial draft of the CBT exercise"""
        intent = state["user_intent"]
        iteration = state["iteration_count"]

        print(f"\n{'=' * 60}")
        print(f"DEBUG DRAFT NODE: intent={repr(intent)[:100]}")
        print(f"DEBUG DRAFT NODE: iteration={iteration}")
        print(f"{'=' * 60}\n")

        # Check for feedback from other agents
        recent_notes = [
            n for n in state["agent_notes"][-5:] if n.get("target_agent") == "Drafter"
        ]
        feedback_context = "\n".join([f"- {n['note']}" for n in recent_notes])

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a clinical psychologist specializing in Cognitive Behavioral Therapy (CBT).
Your task is to create structured, empathetic, and evidence-based CBT exercises.

Guidelines:
1. Structure: Clear sections (Introduction, Steps, Practice, Reflection)
2. Tone: Warm, supportive, non-judgmental
3. Safety: Never provide medical advice or encourage self-harm
4. Evidence-based: Use established CBT techniques
5. Accessibility: Clear language, actionable steps

Format your response as a complete CBT exercise protocol.""",
                ),
                (
                    "human",
                    """Create a CBT exercise for: {intent}

{feedback_context}

{iteration_context}""",
                ),
            ]
        )

        iteration_context = ""
        if iteration > 0:
            iteration_context = f"This is iteration {iteration + 1}. Previous drafts had issues that need addressing."

        messages = prompt.format_messages(
            intent=intent,
            feedback_context=feedback_context or "No specific feedback yet.",
            iteration_context=iteration_context,
        )

        print(f"DEBUG: Calling LLM with intent: {intent[:100]}")
        print(f"DEBUG: Full prompt messages count: {len(messages)}")
        if messages:
            print(
                f"DEBUG: Human message content preview: {str(messages[-1].content)[:150]}..."
            )

        response = await self.llm.ainvoke(messages)
        draft_content = response.content

        print(
            f"DEBUG: LLM response received, length: {len(draft_content) if draft_content else 0}"
        )
        print(
            f"DEBUG: Draft content preview: {draft_content[:100] if draft_content else '[empty]'}..."
        )

        # Log activity
        log_agent_activity(
            session_id=state.get("session_id", "unknown"),
            agent_name=self.name,
            action="drafted_protocol",
            reasoning=f"Created draft for: {intent[:100]}",
        )

        # Create new agent note
        new_note = {
            "agent_name": self.name,
            "note": f"Created draft version {state['current_version'] + 1}",
            "target_agent": None,
            "timestamp": state.get("last_update"),
            "priority": "info",
        }

        result = {
            "current_draft": draft_content,
            "active_agent": self.name,
            "status": "drafting",
            "agent_notes": [new_note],  # Return as list to be appended by reducer
        }

        print(f"DEBUG: draft() returning: {list(result.keys())}\n")
        return result


class SafetyGuardianAgent:
    """Validates content for safety risks and medical advice"""

    def __init__(self, llm=None):
        self.llm = llm or get_llm()
        self.name = "SafetyGuardian"

    async def review(self, state: ProtocolState) -> Dict[str, Any]:
        """Review draft for safety issues"""
        draft = state.get("current_draft")
        if not draft:
            return {"status": "no_draft"}

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a safety reviewer for clinical content.
Your job is to identify:
1. References to self-harm or suicide
2. Medical advice (diagnosis, medication, treatment)
3. Dangerous practices
4. Inappropriate content

Respond with a JSON object:
{{
    "safe": true/false,
    "safety_score": 0.0-1.0,
    "issues": ["list of issues"],
    "recommendations": ["how to fix"]
}}""",
                ),
                ("human", "Review this CBT exercise for safety:\n\n{draft}"),
            ]
        )

        messages = prompt.format_messages(draft=draft)
        response = await self.llm.ainvoke(messages)

        try:
            # Try to parse JSON response
            result = json.loads(response.content)
        except:
            # Fallback if not JSON
            result = {
                "safe": "safe" in response.content.lower(),
                "safety_score": 0.8 if "safe" in response.content.lower() else 0.3,
                "issues": [],
                "recommendations": [response.content],
            }

        safety_score = result.get("safety_score", 0.5)
        is_safe = result.get("safe", safety_score > 0.7)

        # Update safety checks
        safety_checks = state.get("safety_checks", {})
        safety_checks["medical_advice"] = "medical" not in response.content.lower()
        safety_checks["self_harm"] = (
            "self-harm" not in response.content.lower()
            and "suicide" not in response.content.lower()
        )
        safety_checks["overall"] = is_safe

        # Create notes for issues if found
        agent_notes_to_add = []
        if not is_safe or safety_score < 0.8:
            issues = result.get("issues", [])
            for issue in issues:
                agent_notes_to_add.append(
                    {
                        "agent_name": self.name,
                        "note": f"SAFETY ISSUE: {issue}",
                        "target_agent": "Drafter",
                        "timestamp": state.get("last_update"),
                        "priority": "critical",
                    }
                )

        # Log activity
        log_agent_activity(
            session_id=state.get("session_id", "unknown"),
            agent_name=self.name,
            action="safety_review",
            reasoning=f"Safety score: {safety_score}, Safe: {is_safe}",
        )

        return {
            "safety_checks": safety_checks,
            "safety_score": safety_score,
            "status": "reviewed",
            "agent_notes": agent_notes_to_add,  # Return as list to be appended by reducer
            "active_agent": self.name,
        }


class ClinicalCriticAgent:
    """Evaluates clinical appropriateness, tone, and empathy"""

    def __init__(self, llm=None):
        self.llm = llm or get_llm()
        self.name = "ClinicalCritic"

    async def critique(self, state: ProtocolState) -> Dict[str, Any]:
        """Critique draft for clinical quality"""
        draft = state.get("current_draft")
        if not draft:
            return {"status": "no_draft"}

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a senior clinical psychologist reviewing CBT exercises.
Evaluate:
1. Clinical appropriateness (evidence-based techniques)
2. Empathy and tone (warm, supportive, non-judgmental)
3. Structure and clarity
4. Actionability (can users actually do this?)

Respond with JSON:
{{
    "empathy_score": 0.0-1.0,
    "clinical_score": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "strengths": ["list"],
    "weaknesses": ["list"],
    "recommendations": ["how to improve"]
}}""",
                ),
                ("human", "Critique this CBT exercise:\n\n{draft}"),
            ]
        )

        messages = prompt.format_messages(draft=draft)
        response = await self.llm.ainvoke(messages)

        try:
            result = json.loads(response.content)
        except:
            result = {
                "empathy_score": 0.7,
                "clinical_score": 0.7,
                "overall_score": 0.7,
                "strengths": [],
                "weaknesses": [],
                "recommendations": [],
            }

        empathy_score = result.get("empathy_score", 0.7)
        clinical_score = result.get("clinical_score", 0.7)
        overall_score = result.get("overall_score", 0.7)

        # Create feedback notes
        agent_notes_to_add = []
        weaknesses = result.get("weaknesses", [])
        if weaknesses:
            for weakness in weaknesses[:3]:  # Limit to top 3
                agent_notes_to_add.append(
                    {
                        "agent_name": self.name,
                        "note": f"IMPROVEMENT NEEDED: {weakness}",
                        "target_agent": "Drafter",
                        "timestamp": state.get("last_update"),
                        "priority": "warning",
                    }
                )

        # Log activity
        log_agent_activity(
            session_id=state.get("session_id", "unknown"),
            agent_name=self.name,
            action="clinical_critique",
            reasoning=f"Empathy: {empathy_score}, Clinical: {clinical_score}, Overall: {overall_score}",
        )

        return {
            "empathy_score": empathy_score,
            "clinical_score": clinical_score,
            "status": "critiqued",
            "agent_notes": agent_notes_to_add,  # Return as list to be appended by reducer
            "active_agent": self.name,
        }


class SupervisorAgent:
    """Orchestrates the workflow and decides when drafts are ready"""

    def __init__(self, llm=None):
        self.llm = llm or get_llm()
        self.name = "Supervisor"

    async def decide(self, state: ProtocolState) -> Dict[str, Any]:
        """Decide next action based on current state"""
        iteration = state["iteration_count"]
        max_iterations = state["max_iterations"]
        safety_score = state.get("safety_score")
        empathy_score = state.get("empathy_score")
        clinical_score = state.get("clinical_score")

        # Prepare notes to add
        agent_notes_to_add = []

        # Check if we've exceeded max iterations
        if iteration >= max_iterations:
            agent_notes_to_add.append(
                {
                    "agent_name": self.name,
                    "note": f"Reached max iterations ({max_iterations}). Finalizing current draft.",
                    "target_agent": None,
                    "timestamp": state.get("last_update"),
                    "priority": "warning",
                }
            )
            return {
                "next_agent": "HALT",
                "status": "max_iterations_reached",
                "agent_notes": agent_notes_to_add,
                "active_agent": self.name,
            }

        # Check if draft meets quality thresholds
        quality_ok = (
            safety_score is not None
            and safety_score >= 0.8
            and empathy_score is not None
            and empathy_score >= 0.7
            and clinical_score is not None
            and clinical_score >= 0.7
        )

        if quality_ok and state.get("current_draft"):
            # Ready for human review
            agent_notes_to_add.append(
                {
                    "agent_name": self.name,
                    "note": "Draft meets quality thresholds. Ready for human review.",
                    "target_agent": None,
                    "timestamp": state.get("last_update"),
                    "priority": "info",
                }
            )
            # Log activity
            log_agent_activity(
                session_id=state.get("session_id", "unknown"),
                agent_name=self.name,
                action="approved_for_review",
                reasoning=f"Quality thresholds met. Safety: {safety_score}, Empathy: {empathy_score}, Clinical: {clinical_score}",
            )
            return {
                "next_agent": "finalize",
                "status": "ready_for_review",
                "halted": False,
                "agent_notes": agent_notes_to_add,
                "active_agent": self.name,
            }

        # Check if we need another iteration
        needs_revision = (
            safety_score is not None
            and safety_score < 0.8
            or empathy_score is not None
            and empathy_score < 0.7
            or clinical_score is not None
            and clinical_score < 0.7
        )

        if needs_revision and iteration < max_iterations:
            agent_notes_to_add.append(
                {
                    "agent_name": self.name,
                    "note": f"Quality scores below threshold. Requesting revision (iteration {iteration + 1}/{max_iterations})",
                    "target_agent": None,
                    "timestamp": state.get("last_update"),
                    "priority": "warning",
                }
            )
            return {
                "next_agent": "Drafter",
                "status": "needs_revision",
                "agent_notes": agent_notes_to_add,
                "active_agent": self.name,
            }

        # Default: continue with drafting if no draft exists
        if not state.get("current_draft"):
            return {
                "next_agent": "Drafter",
                "status": "initial_draft_needed",
                "agent_notes": agent_notes_to_add,
                "active_agent": self.name,
            }

        return {
            "next_agent": "finalize",
            "status": "awaiting_review",
            "halted": False,
            "agent_notes": agent_notes_to_add,
            "active_agent": self.name,
        }

    async def supervise(self, state: ProtocolState) -> Dict[str, Any]:
        """Wrapper node that runs decide() and returns the decision."""
        decision = await self.decide(state)
        # Don't modify state in place, just return the decision
        return decision

    async def finalize(self, state: ProtocolState) -> Dict[str, Any]:
        """Convert final draft to final_response for Bindu output."""
        draft = state.get("current_draft", "").strip()
        return {
            "final_response": draft or "[empty draft]",
            "halted": True,
            "status": "completed",
            "active_agent": self.name,
        }
