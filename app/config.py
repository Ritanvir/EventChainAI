import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'eventchain.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = None
    BLOCKCHAIN_RPC_URL = os.getenv(
        "BLOCKCHAIN_RPC_URL", "http://127.0.0.1:8545"
    )
    BLOCKCHAIN_CHAIN_ID = int(os.getenv("BLOCKCHAIN_CHAIN_ID", "31337"))
    BLOCKCHAIN_NETWORK_NAME = os.getenv(
        "BLOCKCHAIN_NETWORK_NAME", "Hardhat Local"
    )
    BLOCKCHAIN_DEPLOYMENT_FILE = BASE_DIR / "blockchain" / "deployment.json"
