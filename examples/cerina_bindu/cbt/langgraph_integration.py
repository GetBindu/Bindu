import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load .env from cbt folder
cbt_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=cbt_env_path)

from langchain_openai import ChatOpenAI
from workflow import create_workflow
from state import create_initial_state


def get_llm_client(api_key: Optional[str] = None) -> ChatOpenAI:
    api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    base_url = "https://openrouter.ai/api/v1"
    model_name = "openai/gpt-oss-120b"
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=0.7,
    )


class LangGraphWorkflowAdapter:
    def __init__(self):
        self.workflow = None
        self._initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            llm = get_llm_client()
            self.workflow = create_workflow(llm)
            self._initialized = True

    async def invoke(
        self,
        user_intent: str,
        thread_id: str,
        task_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self._ensure_initialized()

        # Use Cerina's create_initial_state helper to ensure all required fields are present
        input_state = create_initial_state(
            user_intent=user_intent, session_id=thread_id, max_iterations=3
        )

        # Update with our metadata
        input_state["metadata"] = metadata or {}
        input_state["metadata"]["task_id"] = task_id

        config = {"configurable": {"thread_id": thread_id}}

        # Invoke the workflow and get the final state
        try:
            # Use ainvoke directly - simpler and more reliable than manual astream merging
            final_state = await self.workflow.ainvoke(input_state, config)

        except Exception as e:
            import traceback

            print(f"DEBUG: astream error: {e}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            # Fall back to ainvoke if astream fails
            try:
                final_state = await self.workflow.ainvoke(input_state, config)
            except Exception as e2:
                print(f"DEBUG: ainvoke also failed: {e2}")
                raise

        # Convert to dict if it's a Pydantic model, with fallback
        try:
            if hasattr(final_state, "dict"):
                state_dict = final_state.dict()
            elif hasattr(final_state, "model_dump"):
                state_dict = final_state.model_dump()
            elif isinstance(final_state, dict):
                # Already a dict, use as-is
                state_dict = final_state
            else:
                # Try to convert to dict
                try:
                    state_dict = dict(final_state)
                except:
                    # If that fails, try vars()
                    state_dict = (
                        vars(final_state) if hasattr(final_state, "__dict__") else {}
                    )

            # Remove node execution metadata that shouldn't be in the state
            node_names = {
                "init",
                "draft",
                "safety_review",
                "clinical_critique",
                "supervisor",
                "finalize",
                "__pregel_pull__",
            }
            clean_state = {k: v for k, v in state_dict.items() if k not in node_names}

            return clean_state if clean_state else state_dict

        except Exception as e:
            # If conversion fails, try to extract as much as we can
            import json

            try:
                # Try JSON serialization as last resort
                json_str = json.dumps(final_state, default=str)
                parsed = json.loads(json_str)
                # Remove node metadata
                node_names = {
                    "init",
                    "draft",
                    "safety_review",
                    "clinical_critique",
                    "supervisor",
                    "finalize",
                    "__pregel_pull__",
                }
                return {k: v for k, v in parsed.items() if k not in node_names}
            except:
                # Return empty dict if all else fails
                print(f"WARNING: Could not convert final_state to dict: {e}")
                return {}
