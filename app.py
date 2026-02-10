import streamlit as st
from database.db import init_db
from ui.sidebar import render_sidebar
from ui.upload_ui import render_upload_ui
from ui.dashboard_ui import render_dashboard
from ui.validation_ui import validation_ui
from ui.analytics_ui import render_analytics

# ================= CONFIG =================
st.set_page_config(
    page_title="Receipt Vault Analyzer",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= INIT =================
if "init_done" not in st.session_state:
    init_db()
    st.session_state["init_done"] = True

# ================= MAIN LAYOUT =================
def main():
    # Sidebar handling (Navigation + API Key)
    page = render_sidebar()

    # Main Content Area
    if page == "Upload Receipt":
        render_upload_ui()
    elif page == "Validation":
        validation_ui()
    elif page == "Dashboard":
        render_dashboard()
    elif page == "Analytics":
        render_analytics()
    elif page == "Chat with Data":
        from ui.chat_ui import render_chat
        render_chat()

if __name__ == "__main__":
    main()
