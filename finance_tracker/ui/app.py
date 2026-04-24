import streamlit as st

APP_VERSION = "0.3.0"

PAGES = [
    "Dashboard",
    "Accounts",
    "Transactions",
    "Categories",
    "Investments",
    "Import",
]


def build_app():
    st.set_page_config(
        page_title="Personal Finance Tracker",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("""
        <style>
        div[data-testid="stSidebarContent"] input[type="radio"] { display: none; }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        page = st.radio(
            label="nav",
            options=PAGES,
            index=0,
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown(f"**Personal Finance Tracker**  \n`v{APP_VERSION}`")

    if page == "Dashboard":
        st.title("Dashboard")
        st.info("Net worth and expense dashboard — coming in Phase 4.")
    elif page == "Accounts":
        from finance_tracker.ui.accounts_tab import render
        render()
    elif page == "Transactions":
        from finance_tracker.ui.transactions_tab import render
        render()
    elif page == "Categories":
        from finance_tracker.ui.categories_tab import render
        render()
    elif page == "Investments":
        st.title("Investments")
        st.info("Investment tracker — coming in Phase 4.")
    elif page == "Import":
        from finance_tracker.ui.import_tab import render
        render()
