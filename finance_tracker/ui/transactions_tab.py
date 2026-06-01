import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import select, and_
import plotly.express as px

from finance_tracker.database import get_session
from finance_tracker.models import Transaction, Account, Category
from finance_tracker.repositories.account_repository import AccountRepository
from finance_tracker.repositories.transaction_repository import TransactionRepository
from finance_tracker.services.categorisation.pipeline import CategorizationPipeline
from finance_tracker.models.categorisation import CategorizationLog


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
    labels = {"rule": "Rule", "learned": "Learned", "ollama": "Ollama", "manual": "Manual"}
    return labels.get(log_source or "", "-")


def render():
    st.title("Transactions")

    # Filters
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
        search_text = st.text_input("Search description", placeholder="Swiggy, Salary...")
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

    # Load transactions
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

        # Build category map: name -> (parent_name, txn_type)
        cat_map = {
            c.name: (c.parent_name or c.name, c.txn_type)
            for c in session.execute(select(Category)).scalars()
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

        cat_name = txn.category or "Uncategorised"
        parent, txn_type = cat_map.get(cat_name, (cat_name, "expense"))

        rows.append({
            "ID": txn.id,
            "Date": txn.txn_date.strftime("%d %b %Y"),
            "Account": acct.name,
            "Description": desc,
            "Type": txn.dr_cr,
            "Amount (INR)": float(txn.amount),
            "Category": cat_name,
            "Source": _confidence_label(src),
            "_institution": acct.institution,
            "_parent_category": parent,
            "_txn_type": txn_type,
        })

    if not rows:
        st.info("No transactions match the current filters.")
        return

    df = pd.DataFrame(rows)

    # Metrics
    total_dr = df[df["Type"] == "DR"]["Amount (INR)"].sum()
    total_cr = df[df["Type"] == "CR"]["Amount (INR)"].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Transactions", len(rows))
    m2.metric("Total debits", f"{total_dr:,.2f}")
    m3.metric("Total credits", f"{total_cr:,.2f}")

    # Pie charts — use txn_type to correctly classify
    expense_df = df[df["_txn_type"] == "expense"].copy()
    income_df = df[df["_txn_type"] == "income"].copy()

    if not expense_df.empty or not income_df.empty:
        st.markdown("#### Spending Overview")
        pie1, pie2 = st.columns(2)

        with pie1:
            st.markdown("**Expenses by Category**")
            if not expense_df.empty:
                exp_grouped = (
                    expense_df.groupby("_parent_category")["Amount (INR)"]
                    .sum()
                    .reset_index()
                    .rename(columns={"_parent_category": "Category"})
                    .sort_values("Amount (INR)", ascending=False)
                )
                fig1 = px.pie(
                    exp_grouped,
                    names="Category",
                    values="Amount (INR)",
                    hole=0.3,
                )
                fig1.update_traces(textposition="inside", textinfo="percent+label")
                fig1.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No expense transactions.")

        with pie2:
            st.markdown("**Income by Category**")
            if not income_df.empty:
                inc_grouped = (
                    income_df.groupby("_parent_category")["Amount (INR)"]
                    .sum()
                    .reset_index()
                    .rename(columns={"_parent_category": "Category"})
                    .sort_values("Amount (INR)", ascending=False)
                )
                fig2 = px.pie(
                    inc_grouped,
                    names="Category",
                    values="Amount (INR)",
                    hole=0.3,
                )
                fig2.update_traces(textposition="inside", textinfo="percent+label")
                fig2.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No income transactions.")

    # Delete all matching
    with st.expander("Danger zone"):
        st.caption(f"Delete all {len(rows)} transactions matching current filters.")
        if st.button("Delete all matching transactions", type="secondary", key="delete_all"):
            st.session_state["pending_delete_all"] = [r["ID"] for r in rows]

    if "pending_delete_all" in st.session_state:
        ids_to_delete = st.session_state["pending_delete_all"]
        st.warning(
            f"Confirm: permanently delete ALL {len(ids_to_delete)} matching transaction(s)? "
            "This cannot be undone."
        )
        conf1, conf2 = st.columns(2)
        with conf1:
            if st.button("Yes, delete all", type="primary", key="confirm_delete_all"):
                with get_session() as session:
                    TransactionRepository(session).delete_by_ids(ids_to_delete)
                del st.session_state["pending_delete_all"]
                if "txn_rows" in st.session_state:
                    del st.session_state["txn_rows"]
                st.success(f"Deleted {len(ids_to_delete)} transaction(s).")
                st.rerun()
        with conf2:
            if st.button("Cancel", key="cancel_delete_all"):
                del st.session_state["pending_delete_all"]
                st.rerun()

    # Transactions table
    st.markdown("#### Transactions")

    # Add checkbox column for selection
    df_display = df[["ID", "Date", "Account", "Description", "Type",
                      "Amount (INR)", "Category", "Source"]].copy()

    # Bulk actions ABOVE table so they survive reruns
    st.markdown("##### Bulk Actions")
    act_col1, act_col2, act_col3 = st.columns(3)

    with act_col1:
        cat_names = _category_names()
        new_cat = st.selectbox("Correct category", options=cat_names, key="bulk_cat_select")

    with act_col2:
        st.markdown(" ")
        st.markdown(" ")
        if st.button("Apply to selected", type="primary", key="apply_cat"):
            selected_ids = st.session_state.get("selected_ids", [])
            institution = st.session_state.get("selected_institution", "")
            if not selected_ids:
                st.warning("No rows selected.")
            else:
                with get_session() as session:
                    pipeline = CategorizationPipeline(session, institution)
                    for txn_id in selected_ids:
                        pipeline.apply_manual_correction(txn_id, new_cat)
                st.session_state["selected_ids"] = []
                st.success(f"Category updated to '{new_cat}' for {len(selected_ids)} transaction(s).")
                st.rerun()

    with act_col3:
        st.markdown(" ")
        st.markdown(" ")
        selected_ids_for_label = st.session_state.get("selected_ids", [])
        if st.button(
            f"Delete selected ({len(selected_ids_for_label)})",
            type="secondary",
            key="delete_selected",
        ):
            if not selected_ids_for_label:
                st.warning("No rows selected.")
            else:
                st.session_state["pending_delete"] = selected_ids_for_label

    # Delete selected confirmation
    if "pending_delete" in st.session_state:
        ids_to_delete = st.session_state["pending_delete"]
        st.warning(f"Confirm: permanently delete {len(ids_to_delete)} transaction(s)?")
        conf1, conf2 = st.columns(2)
        with conf1:
            if st.button("Yes, delete", type="primary", key="confirm_delete"):
                with get_session() as session:
                    TransactionRepository(session).delete_by_ids(ids_to_delete)
                del st.session_state["pending_delete"]
                st.session_state["selected_ids"] = []
                st.success(f"Deleted {len(ids_to_delete)} transaction(s).")
                st.rerun()
        with conf2:
            if st.button("Cancel", key="cancel_delete"):
                del st.session_state["pending_delete"]
                st.rerun()

    # Render table with selection
    event = st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "Amount (INR)": st.column_config.NumberColumn(format="%.2f"),
        },
        key="txn_table",
    )

    # Capture selection AFTER table renders
    selected_indices = event.selection.rows if event.selection else []
    if selected_indices:
        st.session_state["selected_ids"] = [rows[i]["ID"] for i in selected_indices]
        st.session_state["selected_institution"] = rows[selected_indices[0]]["_institution"]
        st.caption(f"{len(selected_indices)} row(s) selected. Use actions above.")
    elif "selected_ids" not in st.session_state:
        st.session_state["selected_ids"] = []

    # Clear selection
    if st.session_state.get("selected_ids"):
        if st.button("Clear selection", key="clear_selection"):
            st.session_state["selected_ids"] = []
            st.rerun()