import logging
from datetime import date
from decimal import Decimal
from scipy.optimize import brentq
import numpy as np

logger = logging.getLogger(__name__)


def xirr(cashflows: list[tuple[date, float]]) -> float | None:
    """
    Calculate XIRR given a list of (date, amount) tuples.
    Negative amounts = outflows (buys), positive = inflows (sells + current value).
    Returns annualized rate as a float (e.g. 0.15 = 15%) or None if calculation fails.
    """
    if len(cashflows) < 2:
        return None

    dates, amounts = zip(*cashflows)

    # Convert dates to days from first date
    t0 = dates[0]
    days = [(d - t0).days for d in dates]

    def npv(rate):
        return sum(
            amt / (1 + rate) ** (d / 365.0)
            for amt, d in zip(amounts, days)
        )

    try:
        # XIRR is the rate where NPV = 0
        result = brentq(npv, -0.999, 100.0, maxiter=1000)
        return round(result * 100, 2)  # return as percentage
    except Exception as e:
        logger.debug("XIRR calculation failed: %s", e)
        return None