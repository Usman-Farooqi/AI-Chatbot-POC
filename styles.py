"""
styles.py — CSS styles for the Streamlit app.
"""

MAIN_CSS = """
<style>
    /* Tighten sidebar padding and center content vertically */
    [data-testid="stSidebar"] { padding-top: 1rem; background-color: #f8fbfff4;}
    [data-testid="stSidebarUserContent"] {
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 90%;
    }
    /* Slim down the divider between card and metrics */
    [data-testid="stSidebarUserContent"] hr {
        margin: 0.25rem 0.5;
        border-color: rgba(57, 128, 228, 0.25);
    }
    /* Style the vehicle card */
    .vehicle-card {
        background: linear-gradient(135deg, #a3c4f2a6 0%, #3980e4f4 100%);
        border-radius: 12px;
        padding: 22px;
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

    .stAppHeader {
        background-color: #1a468c;
    }
    .stApp { background-color: #1a468c; }

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
    .st-key-oil_change_metric [data-testid="stMetric"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 8px;
    }
    .st-key-insurance_metric [data-testid="stMetric"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 8px;
    }

    /* Hard-stop the outer page scroll — stMain clips its content instead of scrolling.
       overflow:hidden still acts as a scroll container for position:sticky, so
       stBottom (chat input) remains pinned at the bottom correctly. */
    [data-testid="stAppScrollToBottomContainer"] {
        overflow: hidden !important;
    }
    /* Scrollable messages area — target both the keyed stVerticalBlock and its
       stLayoutWrapper parent, which both carry Streamlit's inline height="600px".
       20rem = app header(~3) + block padding-top(~5) + chat header(~5.5)
               + stBottom height(~4.5) + padding-bottom(0.5) + 1.5rem buffer */
    .st-key-messages_area,
    [data-testid="stLayoutWrapper"]:has(> .st-key-messages_area) {
        height: calc(100vh - 20rem) !important;
        max-height: calc(100vh - 20rem) !important;
        overflow-y: auto !important;
    }
    /* Remove the large default padding-bottom (~10rem) on the block container —
       it was there to leave room for stBottom when the page scrolled, but the
       messages container now handles its own scrolling. */
    [data-testid="stMainBlockContainer"] {
        padding-bottom: 0.5rem !important;
    }

    .st-key-clear_btn_container {
        align-items: flex-end !important;
        padding-top: 1.15rem;
    }
    .st-key-clear_btn [data-testid="stBaseButton-secondary"] {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.85rem;
        border-radius: 20px;
        padding: 8px 16px;
        cursor: pointer;
        transition: background 0.2s, color 0.2s;
        font-family: inherit;
    }

    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        background: linear-gradient(135deg, #3980e4f4 0%, #2969c2f4 20%, #2969c2f4 80%, #3980e4f4 100%);
        border-color: rgba(26, 70, 140, 0.2);
    }

    /* Sample question buttons — lighter blue than the main background */
    .st-key-sample_0 [data-testid="stBaseButton-secondary"],
    .st-key-sample_1 [data-testid="stBaseButton-secondary"],
    .st-key-sample_2 [data-testid="stBaseButton-secondary"] {
        background-color: #2557a7 !important;
        border-color: #3068b8 !important;
        color: #ffffff !important;
    }
    .st-key-sample_0 [data-testid="stBaseButton-secondary"]:hover,
    .st-key-sample_1 [data-testid="stBaseButton-secondary"]:hover,
    .st-key-sample_2 [data-testid="stBaseButton-secondary"]:hover {
        background-color: #2e63bc !important;
        border-color: #4078cc !important;
    }

    /* Chat input bottom bar — match main background */
    [data-testid="stBottomBlockContainer"] {
        background-color: #1a468c !important;
    }

    /* Outer chat input box (Emotion-styled wrapper, e1vtqrcf1) */
    [data-testid="stChatInput"] > div,
    .e1vtqrcf1 {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
    }
    [data-testid="stChatInput"] > div:focus-within,
    .e1vtqrcf1:focus-within {
        border-color: rgba(255, 255, 255, 0.55) !important;
    }
    /* Inner BaseUI textarea root and its container div — both carry inputFill gray */
    [data-testid="stChatInput"] [data-baseweb="textarea"],
    [data-testid="stChatInput"] [data-baseweb="textarea"] > div {
        background-color: transparent !important;
        color: #ffffff !important;
    }
    /* Textarea element itself */
    [data-testid="stChatInputTextArea"] {
        color: #ffffff !important;
        caret-color: #ffffff !important;
    }
    [data-testid="stChatInputTextArea"]::placeholder {
        color: rgba(255, 255, 255, 0.5) !important;
    }

</style>
"""

REG_WARNING_CSS = """
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
"""