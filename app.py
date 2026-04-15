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

# Constants for demo purposes — in a real app, these would be dynamic based on the logged-in user and their vehicle(s).
DRIVER_ID = "TX-DL-4471829"
VEHICLE_ID = "1FTFW1E85MFA12345"

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="My Vehicle Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom styles ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Tighten sidebar padding */
    [data-testid="stSidebar"] { padding-top: 1rem; background-color: #f8fbfff4;}
    /* Style the vehicle card */
    .vehicle-card {
        background: linear-gradient(135deg, #a3c4f2a6 0%, #3980e4f4 100%);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid #3980e443;
        position: relative;
    }
    .vehicle-card h3 { color: #16234b; font-size: 1.2rem; }
    .vehicle-card h2 { color: #16234b; font-size: 2.3rem; }
    .vehicle-card p { color: #16234b; font-size: 0.8rem; }

    /* Avatar in vehicle card */
    .vehicle-card .avatar {
        position: absolute;
        top: 16px;
        right: 16px;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background-color: rgba(255, 255, 255, 0.3);
        border: 2px solid rgba(255, 255, 255, 0.6);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .vehicle-card .avatar svg {
        width: 28px;
        height: 28px;
        fill: #16234b;
    }

    /* Sample question buttons in main area */
    .st-key-sample_questions [data-testid="stBaseButton-secondary"] {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.25);
        color: #ffffff;
        font-size: 0.85rem;
        border-radius: 20px;
    }
    .st-key-sample_questions [data-testid="stBaseButton-secondary"]:hover {
        background: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.4);
    }
    .st-key-sample_questions [data-testid="stMarkdownContainer"] p {
        color: #ffffff;
    }

    .stAppHeader {
        background-color: #1a468c;
    }
    .stApp { background-color: #1a468c; }
    [data-testid="stBottomBlockContainer"] { background-color: #1a468c; }
    [data-testid="stChatInput"] [data-baseweb="textarea"] {
        background-color: transparent;
        border: none;
    }
    [data-testid="stChatInput"] [data-baseweb="base-input"] {
        background-color: transparent;
    }
    [data-testid="stChatInput"] > div {
        background-color: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.3);
        border-radius: 8px;
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"] p {
        color: #1a468c;
    }
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] p {
        color: #1a468c;
    }
    [data-testid="stSidebar"] h4 {
        color: #1a468c;
    }
    .st-key-reg_metric [data-testid="stMetric"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 8px;
        transition: background-color 0.3s ease;
    }
    .st-key-mileage_metric [data-testid="stMetric"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 8px;
    }
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        background: linear-gradient(135deg, #3980e4f4 0%, #2969c2f4 20%, #2969c2f4 80%, #3980e4f4 100%);
        border-color: rgba(26, 70, 140, 0.2);
    }
    /* Make sidebar content a flex column so spacer pushes clear button down */
    [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
        min-height: calc(100vh - 4rem);
        display: flex;
        flex-direction: column;
    }

    /* Clear button container pushed to bottom */
    .st-key-clear_btn {
        margin-top: auto;
    }
</style>
""", unsafe_allow_html=True)

# ── Load vehicle info (cached — only calls MCP once per session) ──────────────
@st.cache_resource
def get_cached_vehicle_info():
    return get_vehicle_info(driver_id=DRIVER_ID, car_id=VEHICLE_ID)

try:
    info = get_cached_vehicle_info()
except RuntimeError as e:
    st.error(f"**Failed to load vehicle info:** {e}")
    st.stop()

# ── Session state initialization ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:

    # Vehicle profile card
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

    # Row 1: Current Miles + Registration
    col1, col2 = st.columns(2)
    col1.container(key="mileage_metric").metric("Current Miles", f"{current_mileage:,}")

    if reg_expiry_str:
        try:
            reg_expiry = datetime.strptime(reg_expiry_str, "%Y-%m-%d").date()
            days_until_reg = (reg_expiry - date.today()).days
            if days_until_reg <= 90:
                with col2.container(key="reg_metric"):
                    st.metric("Reg. Expires", f"{days_until_reg} days")
                st.markdown("""
<style>
    .st-key-reg_metric [data-testid="stMetric"] {
        border-radius: 8px;
        padding: 8px;
    }
    .st-key-reg_metric [data-testid="stMetricValue"] p {
        color: #e65100 !important;
    }
    .st-key-reg_metric [data-testid="stMetricLabel"] p {
        color: #e65100 !important;
    }
</style>
""", unsafe_allow_html=True)
            else:
                reg_display = reg_expiry.strftime("%b %Y")
                col2.metric("Reg. Expires", reg_display)
        except ValueError:
            pass

    # Row 2: Oil Change Due + Insurance Expiry
    col3, col4 = st.columns(2)
    # TODO: These are placeholder values — replace with actual data
    # fetched from MCP tools (get_maintenance_records, get_insurance_info)
    col3.metric("Oil Change Due", "52,750 mi")
    col4.metric("Insurance Exp.", "Sep 2026")

    st.divider()

    # Spacer to push clear button to bottom
    st.markdown('<div style="flex-grow: 1;"></div>', unsafe_allow_html=True)

    # Clear button
    with st.container(key="clear_btn"):
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# ── Main chat area ────────────────────────────────────────────────────────────
st.title("My Vehicle Assistant")
st.caption(
    f"Ask me anything about your {vehicle_name} — maintenance, insurance, warranty, or registration."
)

# Welcome message (shown only when conversation is empty)
if not st.session_state.messages:
    st.info(
        f"👋 Hi {driver_name.split()[0]}! I have access to your vehicle documents — "
        f"your driver's manual, insurance card, maintenance records, and warranty info. "
        f"Ask me anything, or pick a sample question from the sidebar."
    )

# Render conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sample question buttons — shown above chat input when no conversation
if not st.session_state.messages:
    sample_questions = [
        "Are my tires due for rotation?",
        "Is my powertrain warranty still active?",
        "What roadside assistance do I have?",
    ]

    with st.container(key="sample_questions"):
        row1 = st.columns(3)
        row2 = st.columns(3)
        for i, question in enumerate(sample_questions):
            col = row1[i] if i < 3 else row2[i - 3]
            if col.button(question, use_container_width=True, key=f"q_{question[:20]}"):
                st.session_state.messages.append({"role": "user", "content": question})
                st.rerun()

# Handle new user input
if prompt := st.chat_input(f"Ask about your {vehicle_name}..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Generate assistant response if the last message is from the user
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        try:
            response_text = st.write_stream(
                chat_engine.stream_chat_response(st.session_state.messages, info)
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )
        except RuntimeError as e:
            error_msg = str(e)
            st.error(f"**Error:** {error_msg}")
            # Remove the unanswered user message so the user can retry
            st.session_state.messages.pop()