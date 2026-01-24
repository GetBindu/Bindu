import uvicorn
import os
import sys

# Ensure the app module is in path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    print("🚀 Starting Unified Bindu Node Server...")
    print("👉 Frontend & API: http://localhost:8000")
    
    uvicorn.run("bindu_node.app.api.server:app", host="0.0.0.0", port=8000, reload=True)
