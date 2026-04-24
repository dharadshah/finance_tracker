import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
import os

from finance_tracker.parsers.registry import available_parsers, PARSER_REGISTRY
from finance_tracker.services.import_service import ImportService


def _parser_label(key: str) -> str:
    return f"{PARSER_REGISTRY[key].INSTITUTION} [{key}]"


def _key_from_label(label: str) -> str:
    return label.split("[")[-1].rstrip("]")


def render():
    st.title("Import Statement")
    st.markdown("Upload a bank statement file to import transactions into the database.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Upload")

        uploaded_file = st.file_uploader(
            "Statement file",
            type=["csv", "pdf", "xls", "xlsx"],
            help="Supported formats: CSV, PDF, Excel",
        )

        parser_choices = [_parser_label(k) for k in available_parsers()]
        parser_label = st.selectbox("Bank / parser", options=parser_choices)

        account_id_str = st.text_input(
            "Account ID (optional)",
            placeholder="Leave blank to auto-match or create",
            help="Find your account ID on the Accounts page.",
        )

        import_btn = st.button("Import Statement", type="primary", use_container_width=True)

    with col2:
        st.subheader("Result")

        if import_btn:
            if uploaded_file is None:
                st.error("Please upload a statement file.")
            else:
                parser_key = _key_from_label(parser_label)

                account_id = None
                if account_id_str.strip():
                    try:
                        account_id = int(account_id_str.strip())
                    except ValueError:
                        st.error("Account ID must be a number.")
                        return

                # Save uploaded file to a temp location
                suffix = Path(uploaded_file.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                try:
                    with st.spinner("Importing..."):
                        service = ImportService()
                        summary = service.import_statement(
                            file_path=tmp_path,
                            parser_key=parser_key,
                            account_id=account_id,
                        )
                finally:
                    os.unlink(tmp_path)

                if summary.success:
                    st.success("Import complete")
                else:
                    st.error("Import failed")

                # Summary table
                st.markdown("#### Summary")
                summary_data = {
                    "Field": ["Account", "Institution", "Account number", "Period",
                              "Transactions imported", "Duplicates skipped", "Total in file"],
                    "Value": [
                        summary.account_name,
                        summary.institution,
                        summary.account_number_masked or "—",
                        summary.statement_period or "—",
                        summary.transactions_inserted,
                        summary.transactions_skipped,
                        summary.total_processed,
                    ],
                }
                st.dataframe(
                    pd.DataFrame(summary_data),
                    use_container_width=True,
                    hide_index=True,
                )

                if summary.errors:
                    st.error("Errors:\n" + "\n".join(f"- {e}" for e in summary.errors))

                if summary.warnings:
                    shown = summary.warnings[:10]
                    with st.expander(f"Warnings ({len(summary.warnings)})"):
                        for w in shown:
                            st.caption(w)
                        if len(summary.warnings) > 10:
                            st.caption(f"... and {len(summary.warnings) - 10} more")

                # Preview
                st.markdown("#### Transactions from this file")
                preview_df = _build_preview(uploaded_file, parser_key)
                if preview_df is not None:
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)
        else:
            st.info("Upload a file and click Import Statement.")


def _build_preview(uploaded_file, parser_key: str):
    try:
        from finance_tracker.parsers.registry import get_parser
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        try:
            parser = get_parser(parser_key)
            result = parser.process(tmp_path)
        finally:
            os.unlink(tmp_path)

        if not result.transactions:
            return None

        return pd.DataFrame([
            {
                "Date": t.txn_date.strftime("%d %b %Y"),
                "Description": t.description,
                "Type": t.dr_cr,
                "Amount (INR)": f"{float(t.amount):,.2f}",
                "Mode": t.mode or "—",
            }
            for t in result.transactions
        ])
    except Exception:
        return None
