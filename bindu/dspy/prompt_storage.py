# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose     |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Prompt storage implementation using JSON file.

This module provides storage for agent prompts in a JSON file. 
It supports both synchronous and asynchronous access,
handling concurrent writes with atomic operations and file locking.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from filelock import FileLock

from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.prompt_storage")

# Default prompt storage path
DEFAULT_PROMPT_FILE = Path("prompts.json")


class PromptStorage:
    """Storage for prompts using a JSON file.

    Format:
    {
        "prompts": {
            "uuid-string": {
                "id": "uuid-string",
                "prompt_text": "...",
                "status": "active",
                "traffic": 1.0,
                "created_at": "iso-timestamp"
            }
        }
    }
    """

    def __init__(self, filepath: Path | str = DEFAULT_PROMPT_FILE):
        self.filepath = Path(filepath)
        # Lock file will be created alongside the JSON file
        self.lock_path = self.filepath.with_suffix(".lock")
        self._ensure_file()
        self._async_lock = asyncio.Lock()  # For async coordination within process

    def _ensure_file(self) -> None:
        """Ensure the JSON file exists with valid structure."""
        if not self.filepath.exists():
            with FileLock(self.lock_path):
                # Double check after acquiring lock
                if not self.filepath.exists():
                    with open(self.filepath, "w") as f:
                        json.dump({"prompts": {}}, f, indent=2)

    def _load_sync(self) -> Dict[str, Any]:
        """Load prompts synchronously with file lock."""
        try:
            with FileLock(self.lock_path):
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    return data.get("prompts", {})
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_sync(self, prompts: Dict[str, Any]) -> None:
        """Save prompts synchronously with atomic write and file lock."""
        temp_path = self.filepath.with_suffix(".tmp")
        with FileLock(self.lock_path):
            with open(temp_path, "w") as f:
                json.dump({"prompts": prompts}, f, indent=2)
            os.replace(temp_path, self.filepath)

    async def _load_async(self) -> Dict[str, Any]:
        """Load prompts asynchronously (blocks for file lock)."""
        # Using FileLock (blocking) because we need cross-process safety.
        # Ideally this should run in executor to avoid blocking event loop.
        try:
            # Run blocking file operation in thread pool
            def _read_with_lock():
                with FileLock(self.lock_path):
                    with open(self.filepath, "r") as f:
                        return json.load(f)

            data = await asyncio.to_thread(_read_with_lock)
            return data.get("prompts", {})
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    async def _save_async(self, prompts: Dict[str, Any]) -> None:
        """Save prompts asynchronously with atomic write (blocks for file lock)."""
        temp_path = self.filepath.with_suffix(".tmp")

        def _write_with_lock():
            with FileLock(self.lock_path):
                with open(temp_path, "w") as f:
                    json.dump({"prompts": prompts}, f, indent=2)
                os.replace(temp_path, self.filepath)

        await asyncio.to_thread(_write_with_lock)

    def _enrich_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Add computed metrics to prompt (mocked for JSON storage)."""
        # Since we don't have task linkage easily available without DB queries,
        # we return default values for metrics.
        # In a real implementation, we might want to query tasks table via passed storage
        # or store metrics in JSON file (updated separately).
        return {
            **prompt,
            "num_interactions": 0,
            "average_feedback_score": None,
        }

    # -------------------------------------------------------------------------
    # Synchronous API (for Prompt class)
    # -------------------------------------------------------------------------

    def insert_prompt_sync(self, text: str, status: str, traffic: float) -> str:
        """Insert a prompt synchronously.

        Args:
            text: Prompt text
            status: Status (active, candidate, etc.)
            traffic: Traffic allocation (0.0 to 1.0)

        Returns:
            Prompt ID (UUID string)
        """
        # We need to lock the whole read-modify-write cycle
        with FileLock(self.lock_path):
            # Read directly here to keep lock held
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    prompts = data.get("prompts", {})
            except (json.JSONDecodeError, FileNotFoundError):
                prompts = {}

            # Check for duplicates (same text) to avoid bloating file
            for pid, p in prompts.items():
                if (
                    p["prompt_text"] == text
                    and p["status"] == status
                    and abs(p["traffic"] - traffic) < 1e-9
                ):
                    return pid

            prompt_id = str(uuid.uuid4())

            # Logic to handle active/candidate constraints
            if status == "active":
                # Deactivate other active prompts
                for pid, p in prompts.items():
                    if p["status"] == "active":
                        p["status"] = "deprecated"
                        p["traffic"] = 0.0
            elif status == "candidate":
                # Deactivate other candidate prompts
                for pid, p in prompts.items():
                    if p["status"] == "candidate":
                        p["status"] = "deprecated"
                        p["traffic"] = 0.0

            prompts[prompt_id] = {
                "id": prompt_id,
                "prompt_text": text,
                "status": status,
                "traffic": traffic,
                # Simple timestamp approximation
                "created_at": str(uuid.uuid1().time),
            }

            # Save directly here to keep lock held
            temp_path = self.filepath.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump({"prompts": prompts}, f, indent=2)
            os.replace(temp_path, self.filepath)

        return prompt_id

    # -------------------------------------------------------------------------
    # Asynchronous API (for server usage)
    # -------------------------------------------------------------------------

    async def get_active_prompt(self) -> Dict[str, Any] | None:
        """Get the active prompt."""
        async with self._async_lock:
            prompts = await self._load_async()
            for p in prompts.values():
                if p["status"] == "active":
                    return self._enrich_prompt(p)
            return None

    async def get_candidate_prompt(self) -> Dict[str, Any] | None:
        """Get the candidate prompt."""
        async with self._async_lock:
            prompts = await self._load_async()
            for p in prompts.values():
                if p["status"] == "candidate":
                    return self._enrich_prompt(p)
            return None

    async def insert_prompt(self, text: str, status: str, traffic: float) -> str:
        """Insert a prompt asynchronously."""
        async with self._async_lock:
            # Use thread for blocking logic to keep event loop free
            # Logic similar to sync but wrapped
            def _logic():
                with FileLock(self.lock_path):
                    try:
                        with open(self.filepath, "r") as f:
                            data = json.load(f)
                            prompts = data.get("prompts", {})
                    except (json.JSONDecodeError, FileNotFoundError):
                        prompts = {}

                    # Check for duplicates
                    for pid, p in prompts.items():
                        if (
                            p["prompt_text"] == text
                            and p["status"] == status
                            and abs(p["traffic"] - traffic) < 1e-9
                        ):
                            return pid

                    prompt_id = str(uuid.uuid4())

                    if status == "active":
                        for pid, p in prompts.items():
                            if p["status"] == "active":
                                p["status"] = "deprecated"
                                p["traffic"] = 0.0
                    elif status == "candidate":
                        for pid, p in prompts.items():
                            if p["status"] == "candidate":
                                p["status"] = "deprecated"
                                p["traffic"] = 0.0

                    prompts[prompt_id] = {
                        "id": prompt_id,
                        "prompt_text": text,
                        "status": status,
                        "traffic": traffic,
                        "created_at": str(uuid.uuid1().time),
                    }

                    temp_path = self.filepath.with_suffix(".tmp")
                    with open(temp_path, "w") as f:
                        json.dump({"prompts": prompts}, f, indent=2)
                    os.replace(temp_path, self.filepath)
                    return prompt_id

            return await asyncio.to_thread(_logic)

    async def update_prompt_traffic(self, prompt_id: str, traffic: float) -> None:
        """Update prompt traffic."""
        async with self._async_lock:
            def _logic():
                with FileLock(self.lock_path):
                    try:
                        with open(self.filepath, "r") as f:
                            data = json.load(f)
                            prompts = data.get("prompts", {})
                    except:
                        return

                    if prompt_id in prompts:
                        prompts[prompt_id]["traffic"] = traffic

                        temp_path = self.filepath.with_suffix(".tmp")
                        with open(temp_path, "w") as f:
                            json.dump({"prompts": prompts}, f, indent=2)
                        os.replace(temp_path, self.filepath)

            await asyncio.to_thread(_logic)

    async def update_prompt_status(self, prompt_id: str, status: str) -> None:
        """Update prompt status."""
        async with self._async_lock:
            def _logic():
                with FileLock(self.lock_path):
                    try:
                        with open(self.filepath, "r") as f:
                            data = json.load(f)
                            prompts = data.get("prompts", {})
                    except:
                        return

                    if prompt_id in prompts:
                        prompts[prompt_id]["status"] = status

                        temp_path = self.filepath.with_suffix(".tmp")
                        with open(temp_path, "w") as f:
                            json.dump({"prompts": prompts}, f, indent=2)
                        os.replace(temp_path, self.filepath)

            await asyncio.to_thread(_logic)

    async def zero_out_all_except(self, prompt_ids: List[str]) -> None:
        """Zero out traffic for all prompts except given IDs."""
        async with self._async_lock:
            def _logic():
                with FileLock(self.lock_path):
                    try:
                        with open(self.filepath, "r") as f:
                            data = json.load(f)
                            prompts = data.get("prompts", {})
                    except:
                        return

                    changed = False
                    for pid, p in prompts.items():
                        if pid not in prompt_ids and p["traffic"] > 0:
                            p["traffic"] = 0.0
                            changed = True

                    if changed:
                        temp_path = self.filepath.with_suffix(".tmp")
                        with open(temp_path, "w") as f:
                            json.dump({"prompts": prompts}, f, indent=2)
                        os.replace(temp_path, self.filepath)

            await asyncio.to_thread(_logic)
