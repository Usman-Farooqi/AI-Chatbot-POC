"""
app.py — Streamlit UI for the Sasser Driver AI Chatbot POC.

Run with:
    streamlit run app.py

Requires a .env file with ANTHROPIC_API_KEY and MCP_URL set (see .env.example).
"""

import streamlit as st
from datetime import date, datetime

import chat_engine
from vehicle_info import get_vehicle_info
from styles import MAIN_CSS, REG_WARNING_CSS

SAMPLE_QUESTIONS = [
    "Are my tires due for rotation?",
    "Is my powertrain warranty still active?",
    "What roadside assistance do I have?",
]

# Constants for demo purposes
DRIVER_ID = "TX-DL-4471829"
VEHICLE_ID = "1FTFW1E85MFA12345"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="My Vehicle Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown(MAIN_CSS, unsafe_allow_html=True)

# ── Load vehicle info ─────────────────────────────────────────────────────────
@st.cache_resource
def get_cached_vehicle_info():
    return get_vehicle_info(driver_id=DRIVER_ID, car_id=VEHICLE_ID)

try:
    info = get_cached_vehicle_info()
except RuntimeError as e:
    st.error(f"**Failed to load vehicle info:** {e}")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    driver_name = info.driver_name
    vehicle_name = info.vehicle_name
    current_mileage = info.current_mileage
    reg_expiry_str = info.registration_expiry

    st.markdown(f"""
<div class="vehicle-card">
    <div class="avatar">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
        </svg>
    </div>
    <h2>{driver_name}</h2>
    <h3>{vehicle_name}</h3>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # Row 1: Current Miles + Oil Change Due
    col1, col2 = st.columns(2)
    col1.container(key="mileage_metric").metric("Current Miles", f"{current_mileage:,} mi")
    col2.container(key="oil_change_metric").metric("Oil Change Due", info.oil_change_due)

    

    # Row 2: Registration Expiry + Insurance Expiry
    col3, col4 = st.columns(2)
    
    if reg_expiry_str:
        try:
            reg_expiry = datetime.strptime(reg_expiry_str, "%Y-%m-%d").date()
            days_until_reg = (reg_expiry - date.today()).days
            if days_until_reg <= 90:
                with col3.container(key="reg_metric"):
                    st.metric("Reg. Expires", f"{days_until_reg} days")
                st.markdown(REG_WARNING_CSS, unsafe_allow_html=True)
            else:
                reg_display = reg_expiry.strftime("%b %Y")
                col2.metric("Reg. Expires", reg_display)
        except ValueError:
            pass

    col4.container(key="insurance_metric").metric("Insurance Exp.", info.insurance_expiry)

# ── Main chat area ────────────────────────────────────────────────────────────
with st.container(key="chat_header"):
    title_col, btn_col = st.columns([5, 2])
    title_col.title("My Vehicle Assistant")
    with btn_col:
        with st.container(key="clear_btn_container"):
            if st.session_state.messages:
                if st.button("🗑️ Clear Conversation", key="clear_btn"):
                    st.session_state.messages = []
                    st.rerun()
    st.caption(
        f"Ask me anything about your {vehicle_name} — maintenance, insurance, warranty, or registration."
    )

if not st.session_state.messages:
    st.info(
        f"👋 Hi {driver_name.split()[0]}! I have access to your vehicle documents — "
        f"your driver's manual, insurance card, maintenance records, and warranty info. "
        f"Ask me anything, or pick a sample question below."
    )
    cols = st.columns(len(SAMPLE_QUESTIONS))
    for i, question in enumerate(SAMPLE_QUESTIONS):
        if cols[i].button(question, key=f"sample_{i}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": question})
            st.rerun()
else:
    # Scrollable message area — height is overridden by CSS to fill available space
    with st.container(key="messages_area", height=600):
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Generate assistant response inline so it streams inside the scroll container
        if st.session_state.messages[-1]["role"] == "user":
            with st.chat_message("assistant"):
                try:
                    response_text = st.write_stream(
                        chat_engine.stream_chat_response(st.session_state.messages, info)
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response_text}
                    )
                except RuntimeError as e:
                    st.error(f"**Error:** {e}")
                    st.session_state.messages.pop()

# Chat input always rendered at bottom by Streamlit
if prompt := st.chat_input(f"Ask about your {vehicle_name}..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()