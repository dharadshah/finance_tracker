from finance_tracker.parsers.base import BaseStatementParser
from finance_tracker.parsers.icici_bank import ICICIBankParser
from finance_tracker.parsers.axis_bank import AxisBankParser
from finance_tracker.parsers.yes_bank import YesBankParser
from finance_tracker.parsers.kuvera import KuveraParser
from finance_tracker.parsers.icici_credit_card import ICICICreditCardParser
from finance_tracker.parsers.axis_credit_card import AxisCreditCardParser
from finance_tracker.parsers.icici_credit_card_pdf import ICICICreditCardPDFParser
from finance_tracker.parsers.nj_india import NJIndiaParser   



# Registry maps a short key to the parser class.
# To add a new bank: import its parser and add one line here.
PARSER_REGISTRY: dict[str, type[BaseStatementParser]] = {
    "icici_bank": ICICIBankParser,
    "yes_bank":   YesBankParser,     # Phase 2 additions
    "axis_bank":  AxisBankParser,
    # "hdfc_bank":  HDFCBankParser,
    # "sbi":        SBIParser,
    "kuvera": KuveraParser,
    "icici_credit_card": ICICICreditCardParser,
    "icici_credit_card_pdf": ICICICreditCardPDFParser,
    "axis_credit_card": AxisCreditCardParser,
    "nj_india":              NJIndiaParser,

}


def get_parser(key: str) -> BaseStatementParser:
    """
    Returns an instance of the parser for the given key.
    Raises KeyError with a helpful message if not found.
    """
    key = key.lower().strip()
    cls = PARSER_REGISTRY.get(key)
    if cls is None:
        available = ", ".join(sorted(PARSER_REGISTRY.keys()))
        raise KeyError(
            f"No parser registered for '{key}'. Available parsers: {available}"
        )
    return cls()


def available_parsers() -> list[str]:
    return sorted(PARSER_REGISTRY.keys())
