"""
Deep State Management - The "Blackboard" Pattern
Rich, structured state that agents share and collaborate on.
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime


def merge_dicts(a: Optional[Dict], b: Optional[Dict]) -> Dict:
    """Merge two dictionaries, with b taking precedence"""
    if a is None:
        return b or {}
    if b is None:
        return a or {}
    result = dict(a)
    result.update(b)
    return result


def append_list(a: List, b: List) -> List:
    """Append two lists"""
    return (a or []) + (b or [])


def last_value_str(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Return the second (latest) non-None value"""
    return b if b is not None else a


def last_value_int(a: Optional[int], b: Optional[int]) -> Optional[int]:
    """Return the second (latest) non-None value"""
    return b if b is not None else a


def last_value_float(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """Return the second (latest) non-None value"""
    return b if b is not None else a


class AgentNote(TypedDict):
    """Notes agents leave for each other on the blackboard"""

    agent_name: str
    note: str
    target_agent: Optional[str]  # If None, note is for all agents
    timestamp: datetime
    priority: str  # "info", "warning", "critical"


class ProtocolDraft(TypedDict):
    """A versioned draft of the CBT exercise"""

    content: str
    version: int
    iteration: int
    created_by: str
    timestamp: datetime
    safety_score: Optional[float]
    empathy_score: Optional[float]
    clinical_score: Optional[float]
    feedback: List[str]  # Feedback from other agents


class ProtocolState(TypedDict):
    """
    The shared state (blackboard) that all agents read from and write to.
    This is the central workspace for the multi-agent collaboration.
    """

    # Core workflow state
    user_intent: str
    session_id: str
    status: Annotated[
        str, last_value_str
    ]  # "initializing", "drafting", "reviewing", "awaiting_approval", "approved", "completed"

    # Draft management
    current_draft: Annotated[
        Optional[str], last_value_str
    ]  # The latest draft content - takes last write
    draft_history: Annotated[List[ProtocolDraft], append_list]  # All previous drafts
    current_version: Annotated[int, last_value_int]
    iteration_count: Annotated[int, last_value_int]
    max_iterations: int  # Safety limit
    final_response: Annotated[Optional[str], last_value_str]  # Final output for user

    # Agent collaboration
    agent_notes: Annotated[List[AgentNote], append_list]  # The blackboard scratchpad
    active_agent: Annotated[
        Optional[str], last_value_str
    ]  # Which agent is currently working
    agent_decisions: Annotated[
        Dict[str, Any], merge_dicts
    ]  # Decisions made by each agent

    # Safety and quality metrics
    safety_checks: Annotated[
        Dict[str, bool], merge_dicts
    ]  # Results from safety guardian
    safety_score: Annotated[Optional[float], last_value_float]
    empathy_score: Annotated[Optional[float], last_value_float]
    clinical_score: Annotated[Optional[float], last_value_float]

    # Human-in-the-loop
    halted: Annotated[
        bool, last_value_int
    ]  # Whether workflow is paused for human review
    human_approved: Annotated[bool, last_value_int]
    human_edits: Annotated[Optional[str], last_value_str]  # Edits made by human

    # Metadata
    start_time: datetime
    last_update: (
        datetime  # Not annotated - updated by nodes managing their own timestamps
    )
    metadata: Annotated[Dict[str, Any], merge_dicts]  # Additional context


def create_initial_state(
    user_intent: str, session_id: str, max_iterations: int = 5
) -> ProtocolState:
    """Create initial state for a new protocol generation"""
    now = datetime.now()
    return ProtocolState(
        user_intent=user_intent,
        session_id=session_id,
        status="initializing",
        current_draft=None,
        draft_history=[],
        current_version=0,
        iteration_count=0,
        max_iterations=max_iterations,
        final_response=None,
        agent_notes=[],
        active_agent=None,
        agent_decisions={},
        safety_checks={},
        safety_score=None,
        empathy_score=None,
        clinical_score=None,
        halted=False,
        human_approved=False,
        human_edits=None,
        start_time=now,
        last_update=now,
        metadata={},
    )


def add_agent_note(
    state: ProtocolState,
    agent_name: str,
    note: str,
    target_agent: Optional[str] = None,
    priority: str = "info",
) -> ProtocolState:
    """Helper to add a note to the blackboard"""
    new_note = AgentNote(
        agent_name=agent_name,
        note=note,
        target_agent=target_agent,
        timestamp=datetime.now(),
        priority=priority,
    )
    state["agent_notes"].append(new_note)
    state["last_update"] = datetime.now()
    return state


def add_draft_version(
    state: ProtocolState,
    content: str,
    created_by: str,
    safety_score: Optional[float] = None,
    empathy_score: Optional[float] = None,
    clinical_score: Optional[float] = None,
) -> ProtocolState:
    """Helper to add a new draft version to history"""
    new_draft = ProtocolDraft(
        content=content,
        version=state["current_version"] + 1,
        iteration=state["iteration_count"],
        created_by=created_by,
        timestamp=datetime.now(),
        safety_score=safety_score,
        empathy_score=empathy_score,
        clinical_score=clinical_score,
        feedback=[],
    )
    state["draft_history"].append(new_draft)
    state["current_version"] = new_draft["version"]
    state["current_draft"] = content
    state["last_update"] = datetime.now()
    return state
