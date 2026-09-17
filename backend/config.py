"""
Configuration settings for VLearn Adaptive AI Tutor Backend
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DATA_DIR = BASE_DIR / "Data"
DATA_DIR = ROOT_DATA_DIR / "vlearn-pack"
SLIDES_DIR = DATA_DIR / "slides"
TRANSCRIPT_DIR = DATA_DIR / "transcript"
CHATLOG_DIR = DATA_DIR / "chatlog"
SURVEY_FILE = BASE_DIR / "Untitled form.csv"
MOCKUP_DIR = BASE_DIR / "mockup"

# LLM Configuration (OpenRouter & Gemini)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash")

# Load from .env if present
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'\"")
        if not OPENROUTER_API_KEY and "OPENROUTER_API_KEY" in os.environ:
            OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
    except Exception as e:
        print(f"[Config] Warning loading .env: {e}")

# Socratic Pedagogy Rules
STREAK_FOR_LEVEL_UP = 2
MAX_ADAPTIVE_LEVEL = 3
DEFAULT_HINT_LEVEL = 1
