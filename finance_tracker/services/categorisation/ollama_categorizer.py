import json
import logging
import requests
from requests.exceptions import ConnectionError, Timeout

from finance_tracker.services.categorisation.base import BaseCategorizer, CategoryResult

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
OLLAMA_TIMEOUT = 30  # seconds


class OllamaCategorizer(BaseCategorizer):
    """
    Layer 3 — local Ollama model as a fallback for unmatched transactions.
    Requires Ollama running locally with llama3.2 pulled.

    If Ollama is not running, this layer returns None gracefully
    and the transaction is marked Uncategorised. No crash, no error shown
    to the user — just a log warning.

    Setup (one-time):
        1. Install Ollama from https://ollama.com
        2. Run: ollama pull llama3.2
        3. Ollama starts automatically on system boot.
    """

    def __init__(self, valid_categories: list[str]):
        self._categories = valid_categories
        self._available: bool | None = None  # cached per pipeline run

    def categorize(
        self,
        description: str,
        institution: str,
        dr_cr: str,
    ) -> CategoryResult | None:
        if not self._is_available():
            return None

        prompt = self._build_prompt(description, dr_cr)

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 30},
                },
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            raw = response.json().get("response", "").strip()
            category = self._extract_category(raw)

            if category:
                logger.debug("Ollama: %r → %r", description, category)
                return CategoryResult(
                    category_name=category,
                    confidence="medium",
                    source="ollama",
                    matched=True,
                )
        except (ConnectionError, Timeout):
            self._available = False
            logger.warning("Ollama not reachable — skipping for this import run.")
        except Exception as e:
            logger.warning("Ollama error for %r: %s", description, e)

        return None

    def _build_prompt(self, description: str, dr_cr: str) -> str:
        direction = "debit (money going out)" if dr_cr == "DR" else "credit (money coming in)"
        categories_list = "\n".join(f"- {c}" for c in self._categories)
        return (
            f"You are a personal finance categorisation assistant.\n"
            f"Classify the following bank transaction into exactly one category "
            f"from the list below. Respond with only the category name, nothing else.\n\n"
            f"Transaction: {description}\n"
            f"Direction: {direction}\n\n"
            f"Categories:\n{categories_list}\n\n"
            f"Category:"
        )

    def _extract_category(self, raw: str) -> str | None:
        raw = raw.strip().strip('"').strip("'")
        # Exact match first
        for cat in self._categories:
            if cat.lower() == raw.lower():
                return cat
        # Partial match fallback
        for cat in self._categories:
            if cat.lower() in raw.lower() or raw.lower() in cat.lower():
                return cat
        logger.debug("Ollama returned unrecognised category: %r", raw)
        return None

    def _is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=3)
            self._available = r.status_code == 200
        except Exception:
            self._available = False
            logger.info(
                "Ollama not running — Layer 3 disabled. "
                "Install from https://ollama.com and run: ollama pull llama3.2"
            )
        return self._available
