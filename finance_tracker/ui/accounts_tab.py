import streamlit as st
import pandas as pd

from finance_tracker.database import get_session
from finance_tracker.models import AccountType
from finance_tracker.repositories.account_repository import AccountRepository


def _load_accounts(include_inactive: bool = False) -> pd.DataFrame:
    with get_session() as session:
        repo = AccountRepository(session)
        accounts = repo.get_all(include_inactive=include_inactive)

    if not accounts:
        return pd.DataFrame(
            columns=["ID", "Name", "Type", "Institution", "Currency", "Active", "Notes"]
        )

    return pd.DataFrame([
        {
            "ID": a.id,
            "Name": a.name,
            "Type": a.account_type,
            "Institution": a.institution,
            "Currency": a.currency,
            "Active": "Yes" if a.is_active else "No",
            "Notes": a.notes or "—",
        }
        for a in accounts
    ])


def render():
    st.title("Accounts")
    st.markdown(
        "All your financial accounts. "
        "Use the **ID** column when importing statements."
    )

    include_inactive = st.checkbox("Show inactive accounts", value=False)

    df = _load_accounts(include_inactive)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Add account")
    st.caption(
        "Closed accounts can be added too — uncheck Active. "
        "You can still import historical statements for inactive accounts."
    )

    with st.form("add_account_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Account name", placeholder="ICICI Savings ...6760")
            account_type = st.selectbox(
                "Account type",
                options=[e.value for e in AccountType],
                index=0,
            )
            institution = st.text_input("Institution", placeholder="ICICI Bank")

        with col2:
            is_active = st.checkbox("Active", value=True)
            notes = st.text_area(
                "Notes (optional)",
                placeholder="Masked account number, branch, or any note",
                height=100,
            )

        submitted = st.form_submit_button("Add Account", type="primary")

    if submitted:
        name = name.strip()
        institution = institution.strip()

        if not name:
            st.error("Account name is required.")
        elif not institution:
            st.error("Institution name is required.")
        else:
            try:
                with get_session() as session:
                    repo = AccountRepository(session)
                    acct = repo.create(
                        name=name,
                        account_type=AccountType(account_type),
                        institution=institution,
                        is_active=is_active,
                        notes=notes.strip() or None,
                    )
                st.success(f"Account created — ID {acct.id}: {acct.name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
