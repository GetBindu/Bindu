from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

from app.core.config import settings
from app.services.agent_service import BinduAgentService
from app.services.repo_service import RepoService

# Initialize Services
agent_service = BinduAgentService()
repo_service = RepoService()

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

class RepoPathsRequest(BaseModel):
    paths: List[str]
    max_chars: Optional[int] = 3000

class ExplainRequest(BaseModel):
    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None

class ReadFileRequest(BaseModel):
    path: str

# --- Agent Endpoints ---

@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": settings.AGENT_NAME, "id": settings.AGENT_ID}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Chat with the Bindu Node Agent."""
    response_text = agent_service.run(req.message, req.context)
    return {"response": response_text}

# --- Repo Helper Endpoints ---

@app.post("/api/repo/find-todos")
async def find_todos(req: RepoPathsRequest):
    return {"result": repo_service.find_todos(req.paths)}

@app.post("/api/repo/summarize")
async def summarize(req: RepoPathsRequest):
    return {"summary": repo_service.summarize_files(req.paths, req.max_chars)}

@app.post("/api/repo/explain")
async def explain(req: ExplainRequest):
    return {"explanation": repo_service.explain_code(req.path, req.start_line, req.end_line)}

@app.get("/api/repo/tree")
async def get_tree():
    return {"tree": repo_service.get_file_tree()}

@app.post("/api/repo/read")
async def read_file_content(req: ReadFileRequest):
    return {"content": repo_service.read_file(req.path)}

# --- Static Frontend ---
static_dir = os.path.join(settings.BASE_DIR, "bindu_node", "app", "static")
if not os.path.exists(static_dir):
    # Fallback/Safety: try relative to this file if BASE_DIR calculation is odd
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

if not os.path.exists(static_dir):
    print(f"CRITICAL WARNING: Static directory not found at {static_dir}")
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/")
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        return {"error": "index.html not found", "path": index_path} 
    return FileResponse(index_path)
