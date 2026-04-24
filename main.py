"""
Finance Tracker — entry point.
Initialises the database and launches the Gradio UI.

Run with:
    python main.py
"""

import logging
from finance_tracker.config import settings
from finance_tracker.database import init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Finance Tracker (env=%s)", settings.app_env)
    logger.info("Database: %s", settings.db_path)

    init_db()
    logger.info("Database initialised")

    # UI import is deferred so DB is ready before Gradio starts
    from finance_tracker.ui.app import build_app
    app = build_app()
    app.launch(server_name="127.0.0.1", server_port=7860, share=False)


if __name__ == "__main__":
    main()
