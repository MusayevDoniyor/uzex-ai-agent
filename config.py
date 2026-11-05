import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load .env specifically from uzex_agent directory
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
load_dotenv()  # also load root .env if any

DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "uzex.db"))

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Server config
PORT = int(os.environ.get("PORT", 8000))
HOST = os.environ.get("HOST", "0.0.0.0")

# Model settings
# gemini-2.5-flash is ultra-fast (~1.1s) and rock solid. gemini-3.8-flash has high demand spikes
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_MODELS = ["gemini-flash-latest", "gemini-3.8-flash"]


