from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CategoryResult:
    """
    Result returned by any categoriser layer.
    category_name must exactly match a name in the categories table.
    """
    category_name: str
    confidence: str        # high | medium | low
    source: str            # rule | learned | ollama | manual
    matched: bool = True


UNMATCHED = CategoryResult(
    category_name="Uncategorised",
    confidence="low",
    source="rule",
    matched=False,
)


class BaseCategorizer(ABC):
    """
    Interface for all categoriser layers.
    Each layer receives a cleaned description and institution name,
    and returns a CategoryResult or None if it cannot match.

    Returning None signals the pipeline to try the next layer.
    Returning a CategoryResult (even Uncategorised) stops the pipeline.
    """

    @abstractmethod
    def categorize(
        self,
        description: str,
        institution: str,
        dr_cr: str,
    ) -> CategoryResult | None:
        """
        Returns a CategoryResult if this layer can categorise the transaction,
        or None to pass to the next layer.
        """
        ...
