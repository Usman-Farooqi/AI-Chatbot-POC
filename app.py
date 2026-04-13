"""
app.py — Streamlit UI for the Sasser Driver AI Chatbot POC.

Run with:
    streamlit run app.py

Requires a .env file with ANTHROPIC_API_KEY set (see .env.example).
"""

import streamlit as st
from datetime import date, datetime

import chat_engine
from document_loader import (
    load_documents_from_mcp,
    get_vehicle_display_name,
    get_driver_name,
    get_current_mileage,
    get_registration_expiry,
)  # New function to load from MCP

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
    [data-testid="stSidebar"] { padding-top: 1rem; }
    /* Style the vehicle card */
    .vehicle-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid #0f3460;
    }
    .vehicle-card h3 { color: #e94560; margin: 0 0 4px 0; font-size: 0.9rem; }
    .vehicle-card h2 { color: #ffffff; margin: 0; font-size: 1.1rem; }
    .vehicle-card p  { color: #a0a0b0; margin: 4px 0 0 0; font-size: 0.8rem; }
    /* Warning badge */
    .reg-warning {
        background: #ff9800;
        color: #000;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-top: 8px;
    }
    /* Sample question buttons */
    div[data-testid="stExpander"] button {
        text-align: left;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Load documents (cached — only reads files once per session) ───────────────
@st.cache_resource
def get_documents():
    return load_documents_from_mcp(driver_id=DRIVER_ID, car_id=VEHICLE_ID)


try:
    bundle = get_documents()
except RuntimeError as e:
    st.error(f"**Failed to load documents:** {e}")
    st.stop()


# ── Session state initialization ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Branding
    st.markdown("## 🚗 AI Chatbot")
    st.markdown("**Driver AI Assistant** — POC")
    st.divider()

    # Vehicle profile card
    driver_name = get_driver_name(bundle)
    vehicle_name = get_vehicle_display_name(bundle)
    current_mileage = get_current_mileage(bundle)
    reg_expiry_str = get_registration_expiry(bundle)

    # Check if registration is within 90 days
    reg_warning = ""
    if reg_expiry_str:
        try:
            reg_expiry = datetime.strptime(reg_expiry_str, "%Y-%m-%d").date()
            days_until_reg = (reg_expiry - date.today()).days
            if days_until_reg <= 90:
                reg_warning = f"⚠️ Registration expires in {days_until_reg} days"
        except ValueError:
            pass

    st.markdown(f"""
<div class="vehicle-card">
    <h3>DRIVER</h3>
    <h2>{driver_name}</h2>
    <p>{vehicle_name}</p>
    {f'<p class="reg-warning">{reg_warning}</p>' if reg_warning else ''}
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    col1.metric("Current Miles", f"{current_mileage:,}")
    if reg_expiry_str:
        try:
            reg_display = datetime.strptime(reg_expiry_str, "%Y-%m-%d").strftime("%b %Y")
            col2.metric("Reg. Expires", reg_display)
        except ValueError:
            pass

    st.divider()

    # Sample questions
    st.markdown("#### Try asking...")
    sample_questions = [
        "When is my next oil change?",
        "Are my tires due for rotation?",
        "What's my insurance deductible if I get in a fender bender?",
        "Is my powertrain warranty still active?",
        "Is my registration due soon?",
        "Does my warranty cover brake pads?",
        "What roadside assistance do I have?",
    ]

    for question in sample_questions:
        if st.button(question, use_container_width=True, key=f"q_{question[:20]}"):
            st.session_state.messages.append({"role": "user", "content": question})
            st.rerun()

    st.divider()

    # Clear button
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # Docs loaded badge
    st.caption(f"📄 5 documents loaded  •  {current_mileage:,} mi")


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
                chat_engine.stream_chat_response(st.session_state.messages, bundle)
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )
        except RuntimeError as e:
            error_msg = str(e)
            st.error(f"**Error:** {error_msg}")
            # Remove the unanswered user message so the user can retry
            st.session_state.messages.pop()
