import streamlit as st
import pandas as pd

from finance_tracker.database import get_session
from finance_tracker.models.transaction import Category

from sqlalchemy import select


def _load_categories() -> pd.DataFrame:
    with get_session() as session:
        cats = session.execute(
            select(Category).order_by(Category.parent_name, Category.name)
        ).scalars().all()

    if not cats:
        return pd.DataFrame(columns=["ID", "Name", "Parent", "Type"])

    return pd.DataFrame([
        {
            "ID": c.id,
            "Name": c.name,
            "Parent": c.parent_name or "—",
            "Type": c.txn_type,
        }
        for c in cats
    ])


def render():
    st.title("Categories")
    st.markdown(
        "Master list of transaction categories. "
        "These are the only categories the categorisation pipeline can assign."
    )

    df = _load_categories()
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} categories defined.")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Add category")
        with st.form("add_category_form"):
            name = st.text_input("Category name", placeholder="e.g. Pet Food")
            parent_name = st.text_input(
                "Parent category (optional)",
                placeholder="e.g. Food",
            )
            txn_type = st.selectbox(
                "Transaction type",
                options=["expense", "income", "investment", "transfer"],
                index=0,
            )
            add_submitted = st.form_submit_button("Add Category", type="primary")

        if add_submitted:
            name = name.strip()
            parent_name = parent_name.strip() or None
            if not name:
                st.error("Category name is required.")
            else:
                try:
                    with get_session() as session:
                        existing = session.execute(
                            select(Category).where(Category.name == name)
                        ).scalar_one_or_none()
                        if existing:
                            st.warning(f"Category '{name}' already exists.")
                        else:
                            session.add(Category(
                                name=name,
                                parent_name=parent_name,
                                txn_type=txn_type,
                            ))
                    st.success(f"Category '{name}' added.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        st.subheader("Edit category")
        with st.form("edit_category_form"):
            category_id = st.number_input("Category ID to edit", min_value=1, step=1)
            new_name = st.text_input("New name (leave blank to keep)")
            new_parent = st.text_input("New parent (leave blank to keep)")
            new_type = st.selectbox(
                "New type",
                options=["expense", "income", "investment", "transfer"],
                index=0,
            )
            edit_submitted = st.form_submit_button("Save Changes", type="primary")

        if edit_submitted:
            try:
                with get_session() as session:
                    cat = session.get(Category, int(category_id))
                    if cat is None:
                        st.error(f"Category ID {category_id} not found.")
                    else:
                        if new_name.strip():
                            cat.name = new_name.strip()
                        if new_parent.strip():
                            cat.parent_name = new_parent.strip()
                        cat.txn_type = new_type
                st.success("Category updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
