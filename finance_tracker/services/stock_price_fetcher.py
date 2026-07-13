import logging
import httpx
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_tracker.models.investment import StockHolding, StockPriceHistory

logger = logging.getLogger(__name__)


class StockPriceFetcher:
    """
    Fetches current stock prices from Yahoo Finance.
    Maps NSE/BSE symbols to Yahoo Finance format.
    """

    def fetch_and_store(self, session: Session) -> dict:
        summary = {"fetched": 0, "failed": 0, "already_current": 0, "errors": []}

        holdings = session.execute(select(StockHolding)).scalars().all()
        if not holdings:
            summary["errors"].append("No holdings found")
            return summary

        today = date.today()

        for holding in holdings:
            symbol = holding.symbol
            exchange = holding.exchange.upper()

            # Convert to Yahoo Finance symbol
            yahoo_symbol = self._to_yahoo_symbol(symbol, exchange)

            try:
                price = self._fetch_price(yahoo_symbol)
                if price is None:
                    summary["failed"] += 1
                    summary["errors"].append(f"No price: {symbol}")
                    continue

                # Check if already stored for today
                existing = session.execute(
                    select(StockPriceHistory).where(
                        StockPriceHistory.symbol == symbol,
                        StockPriceHistory.exchange == exchange,
                        StockPriceHistory.price_date == today,
                    )
                ).scalar()

                if existing:
                    existing.close_price = price
                    summary["already_current"] += 1
                else:
                    session.add(StockPriceHistory(
                        symbol=symbol,
                        exchange=exchange,
                        price_date=today,
                        close_price=price,
                    ))
                    summary["fetched"] += 1

            except Exception as e:
                summary["failed"] += 1
                summary["errors"].append(f"Error fetching {symbol}: {e}")

        session.flush()
        logger.info("Stock price fetch complete: %s", summary)
        return summary

    def _to_yahoo_symbol(self, symbol: str, exchange: str) -> str:
        """Convert NSE/BSE symbol to Yahoo Finance format."""
        exchange = exchange.upper()
        if exchange in ("NSE", "EQ"):
            return f"{symbol}.NS"
        elif exchange in ("BSE", "B", "A"):
            return f"{symbol}.BO"
        return f"{symbol}.NS"  # default to NSE

    def _fetch_price(self, yahoo_symbol: str) -> Decimal | None:
        """Fetch latest price from Yahoo Finance."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }
        try:
            response = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
            response.raise_for_status()
            data = response.json()

            result = data.get("chart", {}).get("result", [])
            if not result:
                return None

            meta = result[0].get("meta", {})
            price = meta.get("regularMarketPrice") or meta.get("previousClose")
            if price:
                return Decimal(str(price))
            return None

        except Exception as e:
            logger.warning("Failed to fetch %s: %s", yahoo_symbol, e)
            return None