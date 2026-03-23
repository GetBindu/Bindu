"""
LangGraph Workflow - The Multi-Agent Orchestration
Implements a Supervisor-Worker pattern with autonomous decision-making.
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from state import ProtocolState, add_draft_version
from agents import (
    DrafterAgent,
    SafetyGuardianAgent,
    ClinicalCriticAgent,
    SupervisorAgent,
)


async def draft_node(state: ProtocolState) -> ProtocolState:
    """Node: Drafter creates/revises draft"""
    result = await drafter.draft(state)

    # Update state with draft
    state["current_draft"] = result.get("current_draft", state.get("current_draft"))
    state["active_agent"] = result.get("active_agent", "Drafter")
    state["status"] = result.get("status", "drafting")
    state["iteration_count"] += 1

    # Add draft to history
    if state["current_draft"]:
        state = add_draft_version(state, state["current_draft"], "Drafter")

    return state


async def safety_review_node(state: ProtocolState) -> ProtocolState:
    """Node: Safety Guardian reviews for safety issues"""
    result = await safety_guardian.review(state)

    # Update safety metrics
    if "safety_checks" in result:
        state["safety_checks"].update(result["safety_checks"])
    if "safety_score" in result:
        state["safety_score"] = result["safety_score"]
    state["active_agent"] = "SafetyGuardian"
    state["status"] = result.get("status", "reviewing")

    return state


async def clinical_critique_node(state: ProtocolState) -> ProtocolState:
    """Node: Clinical Critic evaluates quality"""
    result = await clinical_critic.critique(state)

    # Update quality metrics
    if "empathy_score" in result:
        state["empathy_score"] = result["empathy_score"]
    if "clinical_score" in result:
        state["clinical_score"] = result["clinical_score"]
    state["active_agent"] = "ClinicalCritic"
    state["status"] = result.get("status", "critiquing")

    return state


async def finalize_node(state: ProtocolState) -> ProtocolState:
    result = await supervisor.finalize(state)
    state["status"] = "completed"
    state.update(result)
    return state


def should_continue(
    state: ProtocolState,
) -> Literal[
    "draft", "safety_review", "clinical_critique", "supervisor", "halt", "end"
]:
    """
    Router function: Decides which node to execute next based on current state.
    This implements the autonomous decision-making logic.
    """
    active_agent = state.get("active_agent")
    status = state.get("status", "")
    current_draft = state.get("current_draft")

    print(
        f"DEBUG should_continue: active_agent={active_agent}, status={status}, draft_exists={bool(current_draft)}"
    )

    # If halted, wait for human approval
    if state.get("halted"):
        print("DEBUG: Halted, returning 'end'")
        return "end"

    # If human approved, continue to finalization
    if state.get("human_approved"):
        state["halted"] = False
        print("DEBUG: Human approved, returning 'end'")
        return "end"

    # After drafting, always review safety
    if active_agent == "Drafter":
        print("DEBUG: After Drafter, routing to safety_review")
        return "safety_review"

    # After safety review, critique clinically
    if active_agent == "SafetyGuardian":
        print("DEBUG: After SafetyGuardian, routing to clinical_critique")
        return "clinical_critique"

    # After critique, supervisor decides
    if active_agent == "ClinicalCritic":
        print("DEBUG: After ClinicalCritic, routing to supervisor")
        return "supervisor"

    # Supervisor decides next action
    if active_agent == "Supervisor":
        print(f"DEBUG: Supervisor decision - status: {status}")
        # Check supervisor's decision
        if "needs_revision" in status:
            print("DEBUG: Supervisor says needs_revision, routing back to draft")
            return "draft"  # Route back to drafter for revision
        elif "ready_for_review" in status or "awaiting_review" in status:
            print("DEBUG: Supervisor says ready, routing to finalize")
            return "finalize"
        else:
            print("DEBUG: Supervisor status unclear, routing to end")
            return "end"

    # Default: if no draft exists, start with draft
    if not state.get("current_draft"):
        print("DEBUG: No draft exists, routing to draft")
        return "draft"

    # Default: supervisor decides
    print("DEBUG: Default routing to supervisor")
    return "supervisor"


def init_state(state: ProtocolState) -> ProtocolState:
    print(f"\n{'=' * 60}")
    print("INIT_STATE CALLED")
    print(f"  - state keys: {list(state.keys())}")
    print(f"  - user_intent: {state.get('user_intent', 'NOT SET')}")
    print(f"  - session_id: {state.get('session_id', 'NOT SET')}")
    print(f"  - status: {state.get('status', 'NOT SET')}")
    print(f"{'=' * 60}\n")

    state.setdefault("iteration_count", 0)
    state.setdefault("max_iterations", 3)
    state.setdefault("safety_score", None)
    state.setdefault("empathy_score", None)
    state.setdefault("clinical_score", None)
    state.setdefault("current_draft", "")
    state.setdefault("halted", False)
    # Ensure list fields are initialized as lists
    if "agent_notes" not in state:
        state["agent_notes"] = []
    if "draft_history" not in state:
        state["draft_history"] = []
    if "safety_checks" not in state:
        state["safety_checks"] = {}
    if "agent_decisions" not in state:
        state["agent_decisions"] = {}
    if "metadata" not in state:
        state["metadata"] = {}
    return state


def create_workflow(llm):
    """Create and compile the LangGraph workflow"""
    drafter = DrafterAgent(llm)
    safety_guardian = SafetyGuardianAgent(llm)
    clinical_critic = ClinicalCriticAgent(llm)
    supervisor = SupervisorAgent(llm)
    # Create graph
    workflow = StateGraph(ProtocolState)

    # Add nodes - use the agent methods directly, they return partial state updates
    workflow.add_node("init", init_state)
    workflow.set_entry_point("init")
    workflow.add_edge("init", "draft")
    workflow.add_node("draft", drafter.draft)
    workflow.add_node("safety_review", safety_guardian.review)
    workflow.add_node("clinical_critique", clinical_critic.critique)
    workflow.add_node("supervisor", supervisor.supervise)
    workflow.add_node("finalize", supervisor.finalize)

    # Set entry point
    workflow.set_entry_point("draft")

    # Add conditional edges (autonomous routing)
    workflow.add_conditional_edges(
        "draft",
        should_continue,
        {
            "draft": "draft",
            "safety_review": "safety_review",
            "clinical_critique": "clinical_critique",
            "supervisor": "supervisor",
            "halt": END,
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "safety_review",
        should_continue,
        {
            "draft": "draft",
            "clinical_critique": "clinical_critique",
            "supervisor": "supervisor",
            "halt": END,
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "clinical_critique",
        should_continue,
        {"draft": "draft", "supervisor": "supervisor", "halt": END, "end": END},
    )

    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "draft": "draft",
            "clinical_critique": "clinical_critique",
            "supervisor": "supervisor",
            "finalize": "finalize",
            "halt": END,
            "end": END,
        },
    )

    workflow.add_conditional_edges("finalize", should_continue, {"end": END})

    # Compile workflow (stateless, no persistence)
    app = workflow.compile()
    return app
