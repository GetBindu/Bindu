"""Supervisor orchestrator (real CBT) as a Bindu agent.

This agent wraps the LangGraph workflow from cerina-protocol-foundry:
- Drafter Agent (LangGraph node)
- Safety Guardian (LangGraph node)
- Clinical Critic (LangGraph node)

Instead of calling separate Bindu agents, this Supervisor invokes the
LangGraph workflow internally and maps ProtocolState to Bindu artifacts.

Run: python examples/cerina_bindu/cbt/supervisor_cbt.py
"""

from __future__ import annotations

from uuid import UUID, uuid4

from bindu.penguin.bindufy import bindufy
from bindu.utils.logging import get_logger

from langgraph_integration import LangGraphWorkflowAdapter
from state_mapper import (
    build_langgraph_input,
    protocol_state_to_bindu_artifact,
    bindu_message_from_artifact,
)


logger = get_logger("cerina_bindu.cbt.supervisor")


# Global workflow adapter (singleton)
_workflow_adapter: LangGraphWorkflowAdapter | None = None


def get_workflow_adapter() -> LangGraphWorkflowAdapter:
    """Get or create the LangGraph workflow adapter (singleton).

    Returns:
        Configured LangGraphWorkflowAdapter
    """
    global _workflow_adapter
    if _workflow_adapter is None:
        _workflow_adapter = LangGraphWorkflowAdapter()
    return _workflow_adapter


async def handler(messages: list[dict]):
    """Handle incoming Bindu messages by invoking LangGraph workflow.

    Flow:
    1. Parse Bindu message → extract user intent
    2. Map Bindu context_id → LangGraph thread_id
    3. Invoke LangGraph workflow (Drafter → Safety → Critic)
    4. Map ProtocolState → Bindu Artifact
    5. Return structured CBT exercise

    Args:
        messages: List of Bindu message dictionaries with conversation history

    Returns:
        List with single assistant message containing CBT exercise
    """
    if not messages:
        logger.warning("No messages received")
        return [{"role": "assistant", "content": "No input provided"}]

    # Extract Bindu message metadata
    last_message = messages[-1]
    context_id = UUID(last_message.get("context_id") or str(uuid4()))
    task_id = UUID(last_message.get("task_id") or str(uuid4()))

    print(f"\n{'=' * 80}")
    print("HANDLER ENTRY: Received new request")
    print(f"HANDLER: context_id={context_id}")
    print(f"HANDLER: task_id={task_id}")
    print(f"HANDLER: Full last_message keys: {list(last_message.keys())}")
    print(f"HANDLER: Message role: {last_message.get('role', 'NO ROLE')}")
    print(f"HANDLER: Message content type: {type(last_message.get('content'))}")
    print(f"HANDLER: Message content: {last_message.get('content')}")
    print(f"{'=' * 80}\n")

    logger.info(f"Processing CBT request: context_id={context_id}, task_id={task_id}")

    # Build LangGraph input from Bindu message

    try:
        langgraph_input = build_langgraph_input(messages, context_id, task_id)
        user_intent = langgraph_input["user_intent"]
        thread_id = langgraph_input["thread_id"]

        print("HANDLER: build_langgraph_input result:")
        print(f"  - user_intent: '{user_intent}'")
        print(f"  - thread_id: {thread_id}")
        print(f"  - user_intent length: {len(user_intent)}")
        print(f"  - user_intent hash: {hash(user_intent)}")
        print()

        if not user_intent:
            print("WARNING: user_intent is empty!")
            return [{"role": "assistant", "content": "No user intent provided"}]

        logger.info(f"Invoking LangGraph workflow: thread_id={thread_id}")

        # Get workflow adapter and invoke
        adapter = get_workflow_adapter()

        # initial_state = {
        #     "user_intent": user_intent,
        #     "iteration_count": 0,
        #     "max_iterations": 3,
        #     "safety_score": None,
        #     "empathy_score": None,
        #     "clinical_score": None,
        #     "current_draft": "",
        #     "halted": False,
        # }
        final_state = await adapter.invoke(
            user_intent=user_intent,
            thread_id=thread_id,
            task_id=str(task_id),
            metadata=langgraph_input.get("metadata", {}),
        )

        # Ensure final_state is a dict and has required fields
        if not isinstance(final_state, dict):
            logger.warning(f"final_state is not a dict: {type(final_state)}")
            final_state = final_state if isinstance(final_state, dict) else {}

        # Debug: Check what keys are in final_state
        logger.debug(
            f"DEBUG: Available keys in final_state: {list(final_state.keys())}"
        )
        logger.debug(
            f"DEBUG: current_draft value: {repr(final_state.get('current_draft'))}"
        )
        logger.debug(
            f"DEBUG: final_response value: {repr(final_state.get('final_response'))}"
        )
        logger.debug(f"DEBUG: status value: {final_state.get('status')}")
        logger.debug(f"DEBUG: active_agent value: {final_state.get('active_agent')}")

        # Safe extraction of final response
        final_response = (
            final_state.get("final_response") or final_state.get("current_draft") or ""
        )
        if final_response is None:
            final_response = ""

        # Additional logging for debugging
        if not final_response:
            logger.warning("WARNING: No final_response or current_draft found in state")
            logger.debug(f"DEBUG: Full state: {final_state}")

        final_response_preview = (
            str(final_response)[:100] if final_response else "[empty response]"
        )

        logger.info(f"LangGraph workflow completed: {final_response_preview}")

        # Convert ProtocolState to Bindu Artifact
        artifact_id = uuid4()
        artifact = protocol_state_to_bindu_artifact(final_state, artifact_id)

        # Convert Artifact to Bindu message format (for handler return)
        assistant_messages = bindu_message_from_artifact(artifact)

        # Enhance response with artifact metadata for debugging
        if assistant_messages:
            assistant_messages[0]["metadata"] = artifact.get("metadata", {})

        logger.info(f"CBT exercise generated successfully: artifact_id={artifact_id}")
        return assistant_messages

    except Exception as e:
        logger.error(
            "🔥 HANDLER EXCEPTION — THIS SHOULD PRINT IF WE CRASH", exc_info=True
        )

        import traceback

        logger.error(f"Error processing CBT request: {str(e)}", exc_info=True)
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return [
            {
                "role": "assistant",
                "content": f"Error generating CBT exercise: {str(e)}",
            }
        ]


config = {
    "author": "imdanishakhtar7@gmail.com",
    "name": "cerina_supervisor_cbt",
    "description": "Supervisor orchestrator for Cerina CBT integration with LangGraph workflow.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["../../skills/cbt-supervisor-orchestrator"],
}

if __name__ == "__main__":
    bindufy(config, handler)
