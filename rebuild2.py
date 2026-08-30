from finance_tracker.database import get_session
from finance_tracker.models.investment import MFTransaction, MFHolding
from finance_tracker.models.account import Account
from sqlalchemy import select, delete
from decimal import Decimal
from datetime import date

# NJ India folio → Kuvera scheme name mapping (manually resolved)
NJ_FOLIO_SCHEME_MAP = {
    "1608908/93":   "DSP Flexi Cap Regular Growth Plan",
    "419112094174": "Nippon India Mid Cap Growth Plan",
    "501761028124": "Sundaram Mid Cap Regular Growth Plan",
    "501762072487": "Sundaram Mid Cap Regular Growth Plan",
    "501762175302": "Sundaram Mid Cap Regular Growth Plan",
    "44012585341":  "Nippon India Mid Cap Growth Plan",
}

with get_session() as session:
    kuvera = session.execute(
        select(Account).where(Account.institution == "Kuvera")
    ).scalar()
    account_id = kuvera.id

    txns = session.execute(
        select(MFTransaction).order_by(MFTransaction.txn_date)
    ).scalars().all()

    holdings_map = {}

    for t in txns:
        key = (t.folio_number, t.scheme_name)
        is_buy         = t.order_type == "buy"
        is_kuvera_sell = t.order_type == "sell"
        is_nj_outflow  = (t.direction == "outflow" and t.order_type is None)

        if is_buy:
            if key not in holdings_map:
                holdings_map[key] = {
                    "units_bought": Decimal("0"),
                    "units_sold":   Decimal("0"),
                    "cost_basis":   Decimal("0"),
                    "latest_nav":   t.current_nav or Decimal("0"),
                    "last_date":    t.txn_date,
                }
            holdings_map[key]["units_bought"] += t.units
            holdings_map[key]["cost_basis"]   += t.amount

        elif is_kuvera_sell:
            if key not in holdings_map:
                holdings_map[key] = {
                    "units_bought": Decimal("0"),
                    "units_sold":   Decimal("0"),
                    "cost_basis":   Decimal("0"),
                    "latest_nav":   t.current_nav or Decimal("0"),
                    "last_date":    t.txn_date,
                }
            holdings_map[key]["units_sold"] += abs(t.units)

        elif is_nj_outflow:
            scheme = NJ_FOLIO_SCHEME_MAP.get(t.folio_number)
            if scheme:
                matching_key = (t.folio_number, scheme)
                if matching_key in holdings_map:
                    holdings_map[matching_key]["units_sold"] += abs(t.units)
                else:
                    print(f"WARNING: key {matching_key} not in holdings_map")
            else:
                print(f"WARNING: folio {t.folio_number} not in NJ_FOLIO_SCHEME_MAP")

        if not is_nj_outflow and t.current_nav:
            h = holdings_map.get(key)
            if h and t.txn_date >= h["last_date"]:
                h["latest_nav"] = t.current_nav
                h["last_date"]  = t.txn_date

    # Delete and rebuild
    session.execute(delete(MFHolding).where(MFHolding.account_id == account_id))

    today = date.today()
    count = 0

    for (folio, scheme), h in holdings_map.items():
        net_units = h["units_bought"] - h["units_sold"]
        if net_units <= Decimal("0.001"):
            continue
        proportion      = net_units / h["units_bought"] if h["units_bought"] > 0 else Decimal("0")
        invested_amount = h["cost_basis"] * proportion
        avg_nav         = invested_amount / net_units if net_units > 0 else Decimal("0")

        session.add(MFHolding(
            account_id=account_id,
            scheme_code=f"{folio}_{scheme[:20]}",
            scheme_name=scheme,
            folio_number=folio,
            units=net_units,
            avg_nav=avg_nav,
            invested_amount=invested_amount,
            last_updated=today,
        ))
        count += 1

    print(f"Holdings rebuilt: {count}")