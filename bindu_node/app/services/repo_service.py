import logging
import os
from typing import List, Optional
try:
    from agno.agent import Agent
    from agno.models.azure import AzureOpenAI
    AGNO_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Agno Import Error: {e}")
    Agent = AzureOpenAI = None
    AGNO_AVAILABLE = False

from app.core.config import settings
from app.core.utils import safe_read_file, find_todos_in_text

logger = logging.getLogger("repo_service")

class RepoService:
    def __init__(self):
        self.agent = None
        self._setup_agent()

    def _setup_agent(self):
        if not AGNO_AVAILABLE:
            return
            
        os.environ["AZURE_OPENAI_API_KEY"] = settings.AZURE_GPT_API_KEY
        os.environ["AZURE_OPENAI_ENDPOINT"] = settings.AZURE_GPT_ENDPOINT
        os.environ["AZURE_OPENAI_API_VERSION"] = settings.AZURE_GPT_API_VERSION
        
        try:
            self.agent = Agent(
                name="Repo Helper",
                instructions="You are a senior developer assistant. Summarize code, explain logic, and find bugs.",
                model=AzureOpenAI(
                    id=settings.GPT_DEPLOYMENT,
                    api_key=settings.AZURE_GPT_API_KEY,
                    azure_endpoint=settings.AZURE_GPT_ENDPOINT,
                    api_version=settings.AZURE_GPT_API_VERSION,
                )
            )
        except Exception as e:
            logger.error(f"Failed to init Repo Agent: {e}")

    def find_todos(self, paths: List[str]) -> dict:
        results = {}
        processed_files = set()

        def scan_file(fpath):
            if fpath in processed_files: return
            processed_files.add(fpath)
            try:
                # relative path for display
                rel = os.path.relpath(fpath, settings.BASE_DIR).replace("\\", "/")
                # use safe_read_file logic or direct read since we used os.walk
                text = safe_read_file(settings.BASE_DIR, rel) 
                todos = find_todos_in_text(text)
                if todos:
                    results[rel] = {"todos": todos}
            except Exception:
                pass # Skip binary or unreadable files

        for p in paths:
            abs_p = os.path.abspath(os.path.join(settings.BASE_DIR, p))
            if os.path.isdir(abs_p):
                # Walk directory
                for root, _, files in os.walk(abs_p):
                    for file in files:
                        if file.endswith(('.py', '.js', '.html', '.css', '.md')):
                            scan_file(os.path.join(root, file))
            else:
                # specific file
                scan_file(abs_p)
                
        if not results:
            return {"message": "No TODOs found in the specified paths."}
        return results

    def summarize_files(self, paths: List[str], max_chars: int = 3000) -> str:
        if not self.agent:
            return "Repo Agent not available (agno missing)."
            
        sb = []
        total = 0
        for p in paths:
            try:
                text = safe_read_file(settings.BASE_DIR, p)
                take = text[: max(0, max_chars - total)]
                if take:
                    sb.append(f"--- File: {p} ---\n{take}\n")
                    total += len(take)
            except Exception as e:
                sb.append(f"File {p}: Error {e}")
            if total >= max_chars:
                break
        
        prompt = "Summarize these files (Purpose, Classes, Issues):\n\n" + "\n".join(sb)
        try:
            resp = self.agent.run(prompt)
            return str(resp.content) if hasattr(resp, 'content') else str(resp)
        except Exception as e:
            return f"Agent Error: {e}"

    def explain_code(self, path: str, start: Optional[int], end: Optional[int]) -> str:
        if not self.agent:
            return "Repo Agent not available."
        try:
            snippet = safe_read_file(settings.BASE_DIR, path, start, end)
            prompt = f"Explain this code snippet:\n\n{snippet}"
            resp = self.agent.run(prompt)
            return str(resp.content) if hasattr(resp, 'content') else str(resp)
        except Exception as e:
            return f"Error: {e}"

    def get_file_tree(self, path: str = "") -> List[dict]:
        """
        Returns a recursive list of files and folders.
        path: relative path to start from (default root).
        """
        ignore_list = {'.git', '.venv', '__pycache__', '.idea', '.vscode', 'node_modules', '*.pyc'}
        
        abs_base = os.path.join(settings.BASE_DIR, path)
        if not os.path.exists(abs_base):
            return []

        tree = []
        try:
            with os.scandir(abs_base) as it:
                for entry in sorted(it, key=lambda e: (not e.is_dir(), e.name.lower())):
                    if entry.name in ignore_list:
                        continue
                    
                    rel_path = os.path.join(path, entry.name).replace("\\", "/")
                    node = {
                        "name": entry.name,
                        "path": rel_path,
                        "type": "folder" if entry.is_dir() else "file"
                    }
                    if entry.is_dir():
                        node["children"] = self.get_file_tree(rel_path)
                    
                    tree.append(node)
        except PermissionError:
            pass # Skip folders we can't open
            
        return tree

    def read_file(self, path: str) -> str:
        try:
            return safe_read_file(settings.BASE_DIR, path)
        except Exception as e:
            return f"Error reading file: {e}"
