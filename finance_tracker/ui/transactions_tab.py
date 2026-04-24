import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import select, and_, delete

from finance_tracker.database import get_session
from finance_tracker.models import Transaction, Account, Category
from finance_tracker.repositories.account_repository import AccountRepository
from finance_tracker.repositories.transaction_repository import TransactionRepository
from finance_tracker.services.categorisation.pipeline import CategorizationPipeline


def _account_choices() -> dict[str, int | None]:
    choices = {"All accounts": None}
    with get_session() as session:
        for a in AccountRepository(session).get_all(include_inactive=True):
            choices[f"{a.name} [ID:{a.id}]"] = a.id
    return choices


def _category_names() -> list[str]:
    with get_session() as session:
        return list(
            session.execute(
                select(Category.name).order_by(Category.parent_name, Category.name)
            ).scalars()
        )


def _confidence_label(log_source: str | None) -> str:
    icons = {"rule": "Rule", "learned": "Learned", "ollama": "Ollama", "manual": "Manual"}
    return icons.get(log_source or "", "—")


def render():
    st.title("Transactions")

    # ── Filters ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    account_map = _account_choices()

    with col1:
        account_label = st.selectbox("Account", options=list(account_map.keys()))
    with col2:
        from_date = st.date_input("From date", value=date.today().replace(day=1))
    with col3:
        to_date = st.date_input("To date", value=date.today())

    col4, col5, col6 = st.columns(3)
    with col4:
        dr_cr_filter = st.radio("Type", options=["All", "DR", "CR"], horizontal=True)
    with col5:
        search_text = st.text_input("Search description", placeholder="Swiggy, Salary…")
    with col6:
        source_filter = st.selectbox(
            "Categorised by",
            options=["All", "rule", "learned", "ollama", "manual", "uncategorised"],
            index=0,
        )

    apply = st.button("Apply Filters", type="primary")

    if not (apply or "txn_rows" in st.session_state):
        st.info("Set filters and click Apply Filters.")
        return

    # ── Load transactions ─────────────────────────────────────────────────────
    account_id = account_map[account_label]

    with get_session() as session:
        stmt = select(Transaction, Account).join(
            Account, Transaction.account_id == Account.id
        ).where(
            and_(
                Transaction.txn_date >= from_date,
                Transaction.txn_date <= to_date,
            )
        )
        if account_id:
            stmt = stmt.where(Transaction.account_id == account_id)
        stmt = stmt.order_by(Transaction.txn_date.desc())
        rows_raw = session.execute(stmt).all()

        # Load latest categorisation source per transaction
        from finance_tracker.models.categorisation import CategorizationLog
        from sqlalchemy import func

        log_subq = (
            select(
                CategorizationLog.transaction_id,
                CategorizationLog.source,
            )
            .distinct(CategorizationLog.transaction_id)
            .order_by(
                CategorizationLog.transaction_id,
                CategorizationLog.assigned_at.desc(),
            )
            .subquery()
        )
        log_map = {
            row.transaction_id: row.source
            for row in session.execute(select(log_subq)).all()
        }

    rows = []
    for txn, acct in rows_raw:
        desc = txn.description or ""
        if search_text and search_text.lower() not in desc.lower():
            continue
        if dr_cr_filter != "All" and txn.dr_cr != dr_cr_filter:
            continue
        src = log_map.get(txn.id)
        if source_filter == "uncategorised" and txn.category != "Uncategorised":
            continue
        if source_filter not in ("All", "uncategorised") and src != source_filter:
            continue

        rows.append({
            "ID": txn.id,
            "Date": txn.txn_date.strftime("%d %b %Y"),
            "Account": acct.name,
            "Description": desc,
            "Type": txn.dr_cr,
            "Amount (INR)": float(txn.amount),
            "Category": txn.category or "Uncategorised",
            "Source": _confidence_label(src),
            "_institution": acct.institution,
        })

    if not rows:
        st.info("No transactions match the current filters.")
        return

    df = pd.DataFrame(rows)

    # ── Metrics ───────────────────────────────────────────────────────────────
    total_dr = df[df["Type"] == "DR"]["Amount (INR)"].sum()
    total_cr = df[df["Type"] == "CR"]["Amount (INR)"].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Transactions", len(rows))
    m2.metric("Total debits", f"{total_dr:,.2f}")
    m3.metric("Total credits", f"{total_cr:,.2f}")

    # ── Table with selection ───────────────────────────────────────────────────
    display_cols = ["ID", "Date", "Account", "Description", "Type",
                    "Amount (INR)", "Category", "Source"]

    st.markdown("#### Transactions")
    st.caption("Select rows to bulk-delete or correct categories.")

    event = st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "Amount (INR)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    selected_indices = event.selection.rows if event.selection else []
    selected_ids = [rows[i]["ID"] for i in selected_indices] if selected_indices else []

    # ── Bulk actions ──────────────────────────────────────────────────────────
    if selected_ids:
        st.markdown(f"**{len(selected_ids)} row(s) selected**")
        act_col1, act_col2 = st.columns(2)

        with act_col1:
            st.markdown("##### Correct category")
            cat_names = _category_names()
            new_cat = st.selectbox(
                "New category",
                options=cat_names,
                key="bulk_cat_select",
            )
            if st.button("Apply to selected", type="primary", key="apply_cat"):
                institution = rows[selected_indices[0]]["_institution"]
                with get_session() as session:
                    pipeline = CategorizationPipeline(session, institution)
                    for txn_id in selected_ids:
                        pipeline.apply_manual_correction(txn_id, new_cat)
                st.success(
                    f"Category updated to '{new_cat}' for {len(selected_ids)} transaction(s)."
                )
                st.rerun()

        with act_col2:
            st.markdown("##### Delete selected")
            st.caption("This cannot be undone.")
            if st.button(
                f"Delete {len(selected_ids)} transaction(s)",
                type="secondary",
                key="delete_selected",
            ):
                st.session_state["pending_delete"] = selected_ids

    # ── Delete confirmation ───────────────────────────────────────────────────
    if "pending_delete" in st.session_state:
        ids_to_delete = st.session_state["pending_delete"]
        st.warning(
            f"Confirm: permanently delete {len(ids_to_delete)} transaction(s)? "
            "This cannot be undone."
        )
        conf1, conf2 = st.columns(2)
        with conf1:
            if st.button("Yes, delete", type="primary", key="confirm_delete"):
                with get_session() as session:
                    TransactionRepository(session).delete_by_ids(ids_to_delete)
                del st.session_state["pending_delete"]
                st.success(f"Deleted {len(ids_to_delete)} transaction(s).")
                st.rerun()
        with conf2:
            if st.button("Cancel", key="cancel_delete"):
                del st.session_state["pending_delete"]
                st.rerun()
