"""
Finance Tracker — entry point.

Run with:
    poetry run streamlit run main.py
"""

import sys
from pathlib import Path

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from finance_tracker.database import init_db
from finance_tracker.ui.app import build_app

init_db()
build_app()
