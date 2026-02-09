import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database.queries import fetch_all_receipts
from config.config import CURRENCY_SYMBOL
from ai.insights import generate_ai_insights
from analytics.forecasting import (
    calculate_moving_averages,
    predict_next_month_spending,
    predict_spending_polynomial
)
from analytics.advanced_analytics import (
    detect_subscriptions,
    calculate_burn_rate
)


def render_analytics():
    st.header("📈 Spending Analytics & Intelligence")

    # ---------------- Fetch Data ----------------
    receipts = fetch_all_receipts()

    if not receipts:
        st.info("No receipts found. Upload some receipts to see analytics!")
        return

    df = pd.DataFrame(receipts)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by="date")

    # ---------------- Sidebar Filters ----------------
    st.sidebar.subheader("Analytics Filters")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
        df_filtered = df.loc[mask]
    else:
        df_filtered = df.copy()

    # ---------------- Budget Tracker ----------------
    st.sidebar.divider()
    st.sidebar.subheader("💰 Monthly Budget")

    budget_input = st.sidebar.number_input(
        "Set Limit (₹)",
        min_value=0.0,
        value=st.session_state.get("monthly_budget", 50000.0),
        step=1000.0
    )
    st.session_state["monthly_budget"] = budget_input

    current_month = datetime.now().strftime("%Y-%m")
    current_month_df = df[df["date"].dt.strftime("%Y-%m") == current_month]
    current_spend = current_month_df["amount"].sum()
    days_passed = datetime.now().day

    budget_stats = calculate_burn_rate(current_spend, budget_input, days_passed)

    if budget_stats:
        st.sidebar.progress(
            budget_stats["percent_used"] / 100,
            text=f"{budget_stats['percent_used']:.1f}% Used"
        )
        st.sidebar.caption(
            f"Spent: ₹{current_spend:,.0f} / ₹{budget_input:,.0f}"
        )
        st.sidebar.markdown(f"**Status:** {budget_stats['status']}")
        if budget_stats["projected"] > budget_input:
            st.sidebar.warning(
                f"📉 Projected: ₹{budget_stats['projected']:,.0f}"
            )

    # ---------------- Export ----------------
    st.sidebar.divider()
    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        "📥 Download CSV",
        csv,
        "receipt_analytics.csv",
        "text/csv"
    )

    # ---------------- KPIs ----------------
    st.markdown("### 📊 Key Performance Indicators")

    col1, col2, col3, col4 = st.columns(4)

    total_spending = df_filtered["amount"].sum()
    avg_transaction = df_filtered["amount"].mean() if not df_filtered.empty else 0
    transaction_count = len(df_filtered)

    if not df_filtered.empty:
        cat_group = df_filtered.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_cat = cat_group.index[0]
        top_cat_amt = cat_group.iloc[0]
    else:
        top_cat, top_cat_amt = "N/A", 0

    col1.metric("Total Spending", f"{CURRENCY_SYMBOL}{total_spending:,.2f}")
    col2.metric("Avg Transaction", f"{CURRENCY_SYMBOL}{avg_transaction:,.2f}")
    col3.metric("Receipts Scanned", transaction_count)
    col4.metric("Top Category", top_cat, f"{CURRENCY_SYMBOL}{top_cat_amt:,.2f}")

    st.divider()

    # ---------------- Tabs ----------------
    tab_trends, tab_cats, tab_vendors, tab_advanced, tab_ai = st.tabs([
        "📉 Trends & Forecast",
        "🍩 Categories",
        "🏢 Vendors",
        "🧠 Strategies & Outliers",
        "🤖 AI Insights"
    ])

    # ================== Trends ==================
    with tab_trends:
        monthly_df = (
            df_filtered.set_index("date")
            .resample("M")["amount"]
            .sum()
            .reset_index()
        )

        fig_line = px.line(
            monthly_df,
            x="date",
            y="amount",
            markers=True,
            title="Monthly Spending Trend"
        )

        poly_forecast = predict_spending_polynomial(df, degree=2)
        if poly_forecast is not None:
            fig_line.add_trace(go.Scatter(
                x=poly_forecast["date"],
                y=poly_forecast["predicted_amount"],
                mode="lines",
                name="AI Trend (Poly)",
                line=dict(dash="dash", color="red")
            ))

        st.plotly_chart(fig_line, use_container_width=True)

        daily_spend, ma_7 = calculate_moving_averages(df_filtered, 7)

        fig_ma = go.Figure()
        fig_ma.add_trace(go.Scatter(x=daily_spend.index, y=daily_spend, name="Daily"))
        fig_ma.add_trace(go.Scatter(x=ma_7.index, y=ma_7, name="7-Day Avg"))
        st.plotly_chart(fig_ma, use_container_width=True)

        predicted, avg = predict_next_month_spending(df)
        st.info(
            f"🔮 Predicted next month spend: "
            f"**{CURRENCY_SYMBOL}{predicted:,.2f}** "
            f"(Daily Avg: {CURRENCY_SYMBOL}{avg:,.2f})"
        )

    # ================== Categories ==================
    with tab_cats:
        cat_df = df_filtered.groupby("category")["amount"].sum().reset_index()

        col_a, col_b = st.columns(2)

        with col_a:
            st.plotly_chart(
                px.pie(cat_df, values="amount", names="category", hole=0.4),
                use_container_width=True
            )

        with col_b:
            st.plotly_chart(
                px.treemap(
                    df_filtered,
                    path=[px.Constant("All"), "category", "vendor"],
                    values="amount"
                ),
                use_container_width=True
            )

    # ================== Vendors (FIXED HERE) ==================
    with tab_vendors:
        vendor_df = (
            df_filtered.groupby("vendor")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount")
        )

        top_10 = vendor_df.tail(10)

        fig_bar = px.bar(
            top_10,
            x="amount",
            y="vendor",
            orientation="h",
            title="Top 10 Vendors by Spend",
            text_auto=True
        )

        fig_bar.update_traces(
            texttemplate="%{x:.2s}",
            textposition="outside"
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    # ================== Advanced ==================
    with tab_advanced:
        st.plotly_chart(
            px.box(df_filtered, y="amount", points="all"),
            use_container_width=True
        )

        subs = detect_subscriptions(df)
        if not subs.empty:
            st.dataframe(subs, use_container_width=True)
        else:
            st.success("No recurring subscriptions detected.")

    # ================== AI ==================
    with tab_ai:
        if st.button("Generate AI Report", type="primary"):
            with st.spinner("Analyzing..."):
                insight = generate_ai_insights(df_filtered)
                st.markdown(insight)
