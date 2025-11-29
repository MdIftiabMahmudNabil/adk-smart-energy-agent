"""Configuration management for the Smart Energy Consumption Agent."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LOGS_DIR = PROJECT_ROOT / "logs"
EVALUATION_DIR = PROJECT_ROOT / "evaluation"

# Ensure directories exist
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyD9fY4Fa54rTLMqd_d-F6NavAJJheBraWU")
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Model Configuration
MODEL_NAME = "gemini-2.0-flash-exp"  # Using the latest Gemini model
TEMPERATURE = 0.7
MAX_OUTPUT_TOKENS = 8192

# Agent Configuration
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
SESSION_TIMEOUT = 3600  # 1 hour in seconds

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Dashboard Configuration
DASHBOARD_PORT = 8501
DASHBOARD_TITLE = "Smart Energy Consumption Agent"

# Evaluation Configuration
VALIDATION_TOLERANCE = 0.02  # 2% tolerance for cost calculations
