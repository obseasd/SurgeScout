"""SurgeScout configuration."""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# LLM
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "")

# Moltbook
MOLTBOOK_API_URL = os.getenv("MOLTBOOK_API_URL", "https://www.moltbook.com")
MOLTBOOK_SUBMOLT = os.getenv("MOLTBOOK_SUBMOLT", "lablab")

# SURGE / On-chain
SURGE_API_URL = os.getenv("SURGE_API_URL", "https://api.surge.xyz")
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://sepolia.base.org")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")

# Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8899"))
SECRET_KEY = os.getenv("SECRET_KEY", "surgescout-dev-key")

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
