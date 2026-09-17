"""
VLearn Adaptive AI Tutor - Launcher Script
Launches the unified FastAPI backend & frontend server.
"""

import sys
import io
import uvicorn

# Thiết lập encoding utf-8 để tương thích console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    print("=========================================================")
    print("  🚀 Khởi động VLearn Adaptive AI Tutor (Track D)")
    print("  Sơ đồ tuần tự: docs/sequence_diagram.jpg")
    print("  Giao diện Web:   http://127.0.0.1:8000")
    print("  API Docs:        http://127.0.0.1:8000/docs")
    print("=========================================================")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
