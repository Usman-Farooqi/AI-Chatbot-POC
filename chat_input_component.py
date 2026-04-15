"""
chat_input_component.py — Custom HTML chat input with sample question buttons.
"""

import streamlit as st

SAMPLE_QUESTIONS = [
    "Are my tires due for rotation?",
    "Is my powertrain warranty still active?",
    "What roadside assistance do I have?",
]

def render_chat_input(vehicle_name: str, show_samples: bool = True):
    """Render the custom chat input with optional sample question buttons or clear button."""

    above_input_html = ""
    if show_samples:
        buttons = "".join([
            f'<button class="sample-btn" onclick="submitChat(this.innerText)">{q}</button>'
            for q in SAMPLE_QUESTIONS
        ])
        above_input_html = f'<div class="sample-questions">{buttons}</div>'
    else:
        above_input_html = """
        <div class="clear-row">
            <button class="clear-btn" onclick="clearChat()">🗑️ Clear Conversation</button>
        </div>
        """

    st.html(f"""
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: transparent !important; overflow: hidden; }}

    .chat-bottom {{
        position: fixed;
        bottom: 20px;
        left: 420px;
        right: 40px;
        z-index: 100;
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding: 4px 0;
        font-family: 'Source Sans Pro', sans-serif;
    }}

    .sample-questions {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: flex-end;
    }}

    .sample-btn {{
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.25);
        color: #ffffff;
        font-size: 0.85rem;
        border-radius: 20px;
        padding: 8px 16px;
        cursor: pointer;
        transition: background 0.2s, border-color 0.2s;
        font-family: inherit;
    }}

    .sample-btn:hover {{
        background: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.4);
    }}

    .clear-row {{
        display: flex;
        justify-content: flex-end;
    }}

    .clear-btn {{
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.85rem;
        border-radius: 20px;
        padding: 8px 16px;
        cursor: pointer;
        transition: background 0.2s, color 0.2s;
        font-family: inherit;
    }}

    .clear-btn:hover {{
        background: rgba(255, 100, 100, 0.15);
        border-color: rgba(255, 100, 100, 0.3);
        color: #ffffff;
    }}

    .input-row {{
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 8px;
        padding: 10px 14px;
    }}

    .input-row input {{
        flex: 1;
        background: transparent;
        border: none;
        outline: none;
        color: #ffffff;
        font-size: 1rem;
        font-family: inherit;
    }}

    .input-row input::placeholder {{
        color: rgba(255, 255, 255, 0.5);
    }}

    .send-btn {{
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        width: 32px;
        height: 32px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-size: 1.2rem;
        transition: background 0.2s;
    }}

    .send-btn:hover {{
        background: rgba(255, 255, 255, 0.35);
    }}
</style>

<div class="chat-bottom">
    {above_input_html}
    <div class="input-row">
        <input
            type="text"
            id="chatInput"
            placeholder="Ask about your {vehicle_name}..."
            onkeydown="if(event.key==='Enter')submitChat(this.value)"
            autocomplete="off"
        />
        <button class="send-btn" onclick="submitChat(document.getElementById('chatInput').value)">&#x2191;</button>
    </div>
</div>

<script>
    function submitChat(text) {{
        text = text.trim();
        if (!text) return;
        window.parent.postMessage({{
            type: 'streamlit:setQueryParam',
            key: 'msg',
            value: text
        }}, '*');
        document.getElementById('chatInput').value = '';
    }}

    function clearChat() {{
        window.parent.postMessage({{
            type: 'streamlit:setQueryParam',
            key: 'clear',
            value: '1'
        }}, '*');
    }}
</script>
""")