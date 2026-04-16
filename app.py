"""
app.py — Streamlit UI for the Sasser Driver AI Chatbot POC.

Run with:
    streamlit run app.py

Requires a .env file with ANTHROPIC_API_KEY and MCP_URL set (see .env.example).
"""

import base64

import streamlit as st
from datetime import date, datetime

import chat_engine
from vehicle_info import get_vehicle_info
from styles import MAIN_CSS, REG_WARNING_CSS, STREAMING_AVATAR_CSS


def _svg_avatar(path_d: str) -> str:
    """Encode an SVG icon as a base64 data URI for use as a chat avatar."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="12" r="12" fill="#3980e4"/>'
        f'<path d="{path_d}" fill="white"/>'
        '</svg>'
    )
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"

# Same person path used in the sidebar vehicle card
_PERSON_PATH = (
    "M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4z"
    "m0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"
)
# Material Design "smart_toy" robot icon
_ROBOT_PATH = (
    "M20 9V7c0-1.1-.9-2-2-2h-3c0-1.66-1.34-3-3-3S9 3.34 9 5H6c-1.1 0-2 .9-2 2v2"
    "c-1.66 0-3 1.34-3 3s1.34 3 3 3v4c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-4"
    "c1.66 0 3-1.34 3-3s-1.34-3-3-3zm-2 10H6V7h12v12z"
    "m-9-6c-.83 0-1.5-.67-1.5-1.5S8.17 10 9 10s1.5.67 1.5 1.5S9.83 13 9 13z"
    "m6 0c-.83 0-1.5-.67-1.5-1.5S14.17 10 15 10s1.5.67 1.5 1.5S15.83 13 15 13z"
    "m-6.5 3h7v-2h-7v2z"
)

USER_AVATAR = _svg_avatar(_PERSON_PATH)
ASSISTANT_AVATAR = _svg_avatar(_ROBOT_PATH)


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
                    st.metric("Registration Expires", f"{days_until_reg} days")
                st.markdown(REG_WARNING_CSS, unsafe_allow_html=True)
            else:
                reg_display = reg_expiry.strftime("%b %Y")
                col2.metric("Registration Expires", reg_display)
        except ValueError:
            pass

    col4.container(key="insurance_metric").metric("Insurance Expires", info.insurance_expiry)

# ── Main chat area ────────────────────────────────────────────────────────────
with st.container(key="chat_header"):
    title_col, btn_col = st.columns([5, 2])
    title_col.title("My Vehicle Assistant")
    with btn_col:
        with st.container(key="clear_btn_container"):
            if st.session_state.messages:
                if st.button("Clear Conversation", key="clear_btn"):
                    st.session_state.messages = []
                    st.rerun()
    st.caption(
        f"Ask me anything about your {vehicle_name} — maintenance, insurance, warranty, or registration."
    )

# Scrollable message area — always rendered so the container doesn't appear/disappear
# during the welcome→chat transition, which would cause the sample buttons to linger
# in the DOM while streaming (Streamlit defers full DOM reconciliation until streaming ends).
with st.container(key="messages_area", height=600):
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
        avatars = {"user": USER_AVATAR, "assistant": ASSISTANT_AVATAR}
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar=avatars[message["role"]]):
                st.markdown(message["content"])

        # Generate assistant response inline so it streams inside the scroll container
        if st.session_state.messages[-1]["role"] == "user":
            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                st.markdown(STREAMING_AVATAR_CSS, unsafe_allow_html=True)
                try:
                    response_text = st.write_stream(
                        chat_engine.stream_chat_response(st.session_state.messages, info)
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response_text}
                    )
                    st.rerun()  # Re-render without streaming CSS to stop the pulse animation
                except RuntimeError as e:
                    st.error(f"**Error:** {e}")
                    st.session_state.messages.pop()

# Chat input always rendered at bottom by Streamlit
if prompt := st.chat_input(f"Ask about your {vehicle_name}..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()