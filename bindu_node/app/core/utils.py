import os
import re
from typing import Optional, List

def safe_read_file(base_dir: str, path: str, start: Optional[int] = None, end: Optional[int] = None) -> str:
    """Read file only if it's inside the repo BASE_DIR."""
    candidate = os.path.abspath(os.path.join(base_dir, path))
    if not candidate.replace("\\", "/").startswith(base_dir.replace("\\", "/")):
        raise ValueError("Path is outside the repository root")
    if not os.path.isfile(candidate):
        raise FileNotFoundError(path)

    with open(candidate, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    start_idx = (start - 1) if start and start > 0 else 0
    end_idx = end if end and end > 0 else len(lines)
    selected = ''.join(lines[start_idx:end_idx])
    return selected

def find_todos_in_text(text: str) -> List[dict]:
    """Extract TODOs from text using regex."""
    todos = []
    todo_re = re.compile(r"\b(?:TODO|FIXME)\b", re.IGNORECASE)
    for i, line in enumerate(text.splitlines(), start=1):
        # Skip detection logic lines
        if "if 'TODO' in" in line or 'if "TODO" in' in line:
            continue
        if todo_re.search(line):
            todos.append({"line": i, "text": line.strip()})
    return todos
