import streamlit as st
from pathlib import Path
import pandas as pd
from app import (
    load_bookings,
    save_bookings,
    sync_payments_from_ziina,
    ensure_ui_config,
    load_ui_config,
    render_settings_panel,
)

ADMIN_PASSWORD = "snowadmin123"  # You can change this

st.set_page_config(page_title="Dashboard · SNOW LIWA", page_icon="❄️", layout="wide")

st.title("Dashboard · لوحة التحكم")

if "dashboard_logged_in" not in st.session_state:
    st.session_state["dashboard_logged_in"] = False

if not st.session_state["dashboard_logged_in"]:
    code = st.text_input("Enter admin code to access dashboard:", type="password")
    if st.button("Login"):
        if code == ADMIN_PASSWORD:
            st.session_state["dashboard_logged_in"] = True
            st.success("Access granted.")
        else:
            st.error("Incorrect code.")
    st.stop()

df = load_bookings()
if df.empty:
    st.info("No bookings yet.")
    st.stop()

if st.button("🔄 Sync payment status from Ziina"):
    with st.spinner("Syncing with Ziina..."):
        df = sync_payments_from_ziina(df)
    st.success("Sync completed.")

total_bookings = len(df)
total_tickets = df["tickets"].sum()
total_amount = df["total_amount"].sum()
total_paid = df[df["status"] == "paid"]["total_amount"].sum()
total_pending = df[df["status"] == "pending"]["total_amount"].sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total bookings", int(total_bookings))
c2.metric("Total tickets", int(total_tickets))
c3.metric("Total amount (AED)", f"{total_amount:,.0f}")
c4.metric("Paid (AED)", f"{total_paid:,.0f}")
c5.metric("Pending (AED)", f"{total_pending:,.0f}")

st.markdown("### Update booking status manually")
booking_ids = df["booking_id"].tolist()
selected_id = st.selectbox("Select booking", booking_ids)
new_status = st.selectbox("New status", ["pending", "paid", "cancelled"])
if st.button("Save status"):
    df.loc[df["booking_id"] == selected_id, "status"] = new_status
    save_bookings(df)
    st.success(f"Updated {selected_id} to status: {new_status}")

st.markdown("### Last 25 bookings")
st.dataframe(
    df.sort_values("created_at", ascending=False).head(25),
    use_container_width=True,
)

st.divider()
st.subheader("Landing page settings")
st.caption(
    "هذه الإعدادات تغيّر فقط الواجهة الخاصة بصفحة SNOW LIWA (خلفيات، ألوان، نصوص، خطوط) بدون أي تأثير على منطق الحجز أو بيانات Ziina."
)

ensure_ui_config()
ui_config = load_ui_config()
render_settings_panel(ui_config)
