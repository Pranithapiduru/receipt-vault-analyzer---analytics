# Receipt Vault Analyzer - Dashboard UI
import streamlit as st
import pandas as pd
import plotly.express as px
from database.queries import fetch_all_receipts, delete_receipt
from ai.insights import generate_ai_insights
from config.config import CURRENCY_SYMBOL

def render_dashboard():
    st.header("📊 Spending Dashboard")

    # 1. Fetch Data
    receipts = fetch_all_receipts()
    
    if not receipts:
        st.info("No receipts found. Go to 'Upload Receipt' to add some!")
        return

    df = pd.DataFrame(receipts)
    # Ensure date is datetime for better chart handling
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by="date", ascending=False)

    # 2. Key Metrics
    total_spend = df["amount"].sum()
    total_tax = df["tax"].sum()
    total_receipts = len(df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Spending", f"{CURRENCY_SYMBOL}{total_spend:,.2f}")
    c2.metric("Total Tax Paid", f"{CURRENCY_SYMBOL}{total_tax:,.2f}")
    c3.metric("Receipts Scanned", total_receipts)

    st.divider()

    # 3. Stored Receipts (Excel-like Scrollable Table)
    st.subheader("📜 Stored Receipts")
    
    # --- Advanced Filters ---
    st.markdown("##### 🔍 Filter Receipts")
    f1, f2, f3 = st.columns(3)
    with f1:
        sb_bill = st.text_input("Bill ID", placeholder="Filter by ID...")
    with f2:
        sb_vendor = st.text_input("Vendor", placeholder="Filter by vendor...")
    with f3:
        sb_subtotal = st.text_input(f"Subtotal ({CURRENCY_SYMBOL})", placeholder="Filter by subtotal...")
    
    f4, f5, _ = st.columns(3)
    with f4:
        sb_tax = st.text_input(f"Tax ({CURRENCY_SYMBOL})", placeholder="Filter by tax...")
    with f5:
        sb_amount = st.text_input(f"Total ({CURRENCY_SYMBOL})", placeholder="Filter by total...")

    if not df.empty:
        # Filtering Logic
        if sb_bill:
            df = df[df["bill_id"].str.lower().str.contains(sb_bill.lower(), na=False)]
        if sb_vendor:
            df = df[df["vendor"].str.lower().str.contains(sb_vendor.lower(), na=False)]
        if sb_subtotal:
            df = df[df["subtotal"].astype(str).str.contains(sb_subtotal, na=False)]
        if sb_tax:
            df = df[df["tax"].astype(str).str.contains(sb_tax, na=False)]
        if sb_amount:
            df = df[df["amount"].astype(str).str.contains(sb_amount, na=False)]

        # Add a selection column for deletion
        df_display = df.copy()
        df_display.insert(0, "Select", False)
        
        # Format the dataframe for display
        # We use data_editor to allow the "Select" column to be interactive
        edited_df = st.data_editor(
            df_display,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Delete?",
                    help="Select receipts to delete",
                    default=False,
                ),
                "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "vendor": "Vendor",
                "bill_id": "Bill ID",
                "subtotal": st.column_config.NumberColumn(f"Subtotal ({CURRENCY_SYMBOL})", format=f"{CURRENCY_SYMBOL}%.2f"),
                "tax": st.column_config.NumberColumn(f"Tax ({CURRENCY_SYMBOL})", format=f"{CURRENCY_SYMBOL}%.2f"),
                "amount": st.column_config.NumberColumn(f"Total ({CURRENCY_SYMBOL})", format=f"{CURRENCY_SYMBOL}%.2f"),
            },
            disabled=["bill_id", "vendor", "date", "amount", "tax", "subtotal"],
            hide_index=True,
            use_container_width=True,
        )

        # Batch Delete Button
        if st.button("🗑️ Delete Selected Receipts", type="secondary", use_container_width=True):
            to_delete = edited_df[edited_df["Select"] == True]
            if not to_delete.empty:
                for bid in to_delete["bill_id"]:
                    delete_receipt(bid)
                st.success(f"Successfully deleted {len(to_delete)} receipt(s)")
                st.rerun()
            else:
                st.warning("No receipts selected for deletion")
    else:
        st.info("No receipts found")

    st.divider()

    # 4. AI Insights (Moved to bottom of Dashboard for quick view if needed, or kept purely in Analytics)
    # Removing charts from here as they are now in a separate page
