"""Map Cerina ProtocolState to/from Bindu artifacts and messages."""

from uuid import UUID
from typing import Any, Dict, List

from bindu.common.protocol.types import Artifact, Part


def extract_text_from_bindu_message(messages: List[Dict[str, Any]]) -> str:
    """Extract user input text from Bindu message format.

    Args:
        messages: List of Bindu message dictionaries

    Returns:
        User's text input
    """
    if not messages:
        return ""

    last_message = messages[-1]

    print(f"\nDEBUG extract_text: Full message: {last_message}")
    print(f"DEBUG extract_text: Message keys: {list(last_message.keys())}")
    content_val = last_message.get("content")
    print(f"DEBUG extract_text: Type of 'content': {type(content_val)}")
    print(f"DEBUG extract_text: Value of 'content': {content_val}")

    # Try to extract text from different possible formats
    # Format 1: "content" field (string - most common)
    if "content" in last_message:
        content = last_message["content"]
        if isinstance(content, str):
            text = content.strip()
            print(f"DEBUG extract_text: Found in 'content' (string): {text[:80]}...")
            return text
        # If content is a dict, try to extract text from it
        elif isinstance(content, dict):
            if "text" in content:
                text = content["text"]
                if isinstance(text, str):
                    text = text.strip()
                    print(
                        f"DEBUG extract_text: Found in 'content.text': {text[:80]}..."
                    )
                    return text
            # Try body or message field in content dict
            for key in ["body", "message", "value"]:
                if key in content and isinstance(content[key], str):
                    text = content[key].strip()
                    print(
                        f"DEBUG extract_text: Found in 'content.{key}': {text[:80]}..."
                    )
                    return text

    # Format 2: "parts" field (alternative format)
    parts = last_message.get("parts", [])
    if parts and isinstance(parts, list):
        text_parts = []
        for p in parts:
            if isinstance(p, dict):
                if p.get("kind") == "text":
                    text_parts.append(p.get("text", ""))
                elif "text" in p:
                    text_parts.append(p["text"])
        text = " ".join(filter(None, text_parts)).strip()
        if text:
            print(f"DEBUG extract_text: Found in 'parts': {text[:80]}...")
            return text

    # Format 3: "message" field
    if "message" in last_message:
        text = last_message["message"]
        if isinstance(text, str):
            text = text.strip()
            print(f"DEBUG extract_text: Found in 'message' (string): {text[:80]}...")
            return text

    # Format 4: "text" field
    if "text" in last_message:
        text = last_message["text"]
        if isinstance(text, str):
            text = text.strip()
            print(f"DEBUG extract_text: Found in 'text': {text[:80]}...")
            return text

    print("DEBUG extract_text: No text found, returning empty string")
    return ""


def build_langgraph_input(
    bindu_messages: List[Dict[str, Any]],
    context_id: UUID,
    task_id: UUID,
) -> Dict[str, Any]:
    """Convert Bindu message to LangGraph workflow input.

    Args:
        bindu_messages: Bindu message history
        context_id: Bindu context ID (maps to LangGraph thread_id)
        task_id: Bindu task ID

    Returns:
        LangGraph input dictionary
    """
    user_input = extract_text_from_bindu_message(bindu_messages)

    # Map Bindu context_id to LangGraph thread_id
    # Format: "bindu_{context_id}" allows multi-turn conversations
    thread_id = f"bindu_{context_id}"

    return {
        "user_intent": user_input,
        "thread_id": thread_id,
        "task_id": str(task_id),
        # Add any other metadata from Bindu messages
        "metadata": {
            "context_id": str(context_id),
            "task_id": str(task_id),
        },
    }


def protocol_state_to_bindu_artifact(
    final_state: Dict[str, Any], artifact_id: UUID
) -> Artifact:
    # Convert ProtocolState → dict if needed
    if hasattr(final_state, "dict"):
        try:
            final_state = final_state.dict()
        except Exception as e:
            # If dict() fails, try model_dump or vars
            print(f"DEBUG: Failed to call .dict(): {e}")
            if hasattr(final_state, "model_dump"):
                try:
                    final_state = final_state.model_dump()
                except Exception as e2:
                    print(f"DEBUG: Failed to call .model_dump(): {e2}")
                    final_state = (
                        vars(final_state) if hasattr(final_state, "__dict__") else {}
                    )
            else:
                final_state = (
                    vars(final_state) if hasattr(final_state, "__dict__") else {}
                )

    # Debug: print available keys
    print(
        f"DEBUG: Available keys in final_state: {list(final_state.keys()) if isinstance(final_state, dict) else 'Not a dict'}"
    )

    # Extract fields from the proper ProtocolState structure
    final_response = final_state.get("current_draft", "")
    draft_history = final_state.get("draft_history", [])
    agent_notes = final_state.get("agent_notes", [])
    safety_score = final_state.get("safety_score")
    empathy_score = final_state.get("empathy_score")
    clinical_score = final_state.get("clinical_score")
    safety_checks = final_state.get("safety_checks", {})
    agent_decisions = final_state.get("agent_decisions", {})
    trace = final_state.get("trace", [])

    parts: List[Part] = [
        {"kind": "text", "text": final_response or "[No draft generated]"}
    ]

    # Include structured debugging metadata
    parts.append(
        {
            "kind": "data",
            "data": {
                "draft": final_response,
                "draft_history": draft_history,
                "safety_score": safety_score,
                "empathy_score": empathy_score,
                "clinical_score": clinical_score,
                "safety_checks": safety_checks,
                "agent_decisions": agent_decisions,
                "agent_notes": agent_notes,
                "trace": final_state.get("trace", []),
            },
        }
    )

    return {
        "artifact_id": artifact_id,
        "name": "cbt_exercise",
        "description": "CBT exercise generated via Cerina Protocol Foundry (LangGraph)",
        "parts": parts,
        "metadata": {
            "source": "cerina",
            "pipeline": "drafter → safety → critic → supervisor",
            "final_draft": final_response,
            "draft_history": draft_history,
            "safety_score": safety_score,
            "empathy_score": empathy_score,
            "clinical_score": clinical_score,
            "safety_checks": safety_checks,
            "agent_decisions": agent_decisions,
            "agent_notes": agent_notes,
            "trace": final_state.get("trace", []),
        },
    }


def bindu_message_from_artifact(artifact: Artifact) -> List[Dict[str, Any]]:
    text_parts = [
        p.get("text", "") for p in artifact.get("parts", []) if p.get("kind") == "text"
    ]
    content = " ".join(text_parts).strip()

    return [
        {
            "role": "assistant",
            "content": content,
            "artifact": artifact,  # include entire artifact for UI or downstream agents
        }
    ]
