import streamlit as st
import os
import requests
import base64
from prompts import get_prompt, TOPICS

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EcoWise AI",
    page_icon="🌿",
    layout="centered"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f9fdf9; }

    .topic-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 6px;
    }

    /* Quick question buttons */
    div[data-testid="stHorizontalBlock"] .stButton > button {
        border: 1.5px solid #66BB6A !important;
        border-radius: 20px !important;
        background: transparent !important;
        color: #2E7D32 !important;
        font-size: 13px !important;
        padding: 8px 10px !important;
    }
    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        background: #e8f5e9 !important;
    }

    /* Hide streamlit default footer & extra space */
    footer { visibility: hidden !important; }
    .block-container { padding-bottom: 20px !important; }

    /* Sidebar footer */
    .sidebar-footer {
        font-size: 11px;
        color: #9E9E9E;
        text-align: center;
        padding: 8px 4px;
        border-top: 1px solid #C8E6C9;
        margin-top: 8px;
        line-height: 1.8;
    }

    /* Clean file uploader */
    [data-testid="stFileUploader"] {
        background: transparent !important;
    }
    [data-testid="stFileUploadDropzone"] {
        background: transparent !important;
        border: 1.5px dashed #66BB6A !important;
        border-radius: 12px !important;
        padding: 6px 14px !important;
        min-height: unset !important;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        background: #e8f5e9 !important;
    }
    [data-testid="stFileUploadDropzone"] span { display: none !important; }
    [data-testid="stFileUploadDropzone"] small { display: none !important; }

    /* Smooth fade for chat messages */
    [data-testid="stChatMessage"] {
        animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Green spinner */
    .stSpinner > div {
        border-top-color: #2E7D32 !important;
    }

    /* Chat input focus glow */
    [data-testid="stChatInput"] textarea:focus {
        border-color: #2E7D32 !important;
        box-shadow: 0 0 0 2px #66BB6A44 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Topic Detection ───────────────────────────────────────────────────────────
def detect_topic(question: str) -> str:
    q = question.lower()

    water_keywords = [
        "water", "rain", "tap", "irrigation", "river", "drink",
        "shower", "leak", "groundwater", "harvest", "drought",
        "well", "pond", "dam", "pipe", "borewell", "toilet",
        "flush", "bucket", "tank", "rainwater", "moisture"
    ]
    energy_keywords = [
        "energy", "electricity", "solar", "led", "power", "light",
        "bulb", "battery", "appliance", "renewable", "wind", "bill",
        "fan", "ac", "air conditioner", "heater", "geyser", "fridge",
        "refrigerator", "generator", "inverter", "watt", "plug",
        "switch", "fuel", "petrol", "diesel"
    ]
    waste_keywords = [
        "waste", "recycle", "plastic", "garbage", "trash", "compost",
        "e-waste", "ewaste", "landfill", "dispose", "packaging", "pollution",
        "bin", "dustbin", "litter", "junk", "scrap", "dump", "sewage",
        "phone", "laptop", "cloth", "organic", "bottle", "bag",
        "wrapper", "biodegradable"
    ]
    climate_keywords = [
        "climate", "carbon", "footprint", "global warming", "emission",
        "co2", "greenhouse", "temperature", "sustainable", "environment",
        "ozone", "deforestation", "tree", "forest", "smog", "cyclone",
        "heatwave", "glacier", "sea level", "biodiversity", "ecosystem"
    ]

    keyword_map = {
        "Water Conservation": water_keywords,
        "Energy Saving":      energy_keywords,
        "Waste Management":   waste_keywords,
        "Climate Action":     climate_keywords,
    }

    scores = {
        topic: sum(1 for k in keywords if k in q)
        for topic, keywords in keyword_map.items()
    }

    best = max(scores, key=scores.get)

    # Tie-breaker: first keyword match wins
    if list(scores.values()).count(scores[best]) > 1:
        for word in q.split():
            for topic, keywords in keyword_map.items():
                if word in keywords:
                    return topic

    return best if scores[best] > 0 else "General Sustainability"

# ── Groq Text API ─────────────────────────────────────────────────────────────
def ask_groq(system_prompt, chat_history, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": system_prompt}] + chat_history
    payload  = {"model": "llama-3.3-70b-versatile", "messages": messages,
                 "temperature": 0.7, "max_tokens": 600}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "⚠️ No internet connection. Please check your network and try again."
    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        if r.status_code == 401:
            return "⚠️ Invalid API key. Please check your Groq API key."
        try:    err = r.json().get("error", {}).get("message", str(e))
        except: err = str(e)
        return f"⚠️ API error: {err}"
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ── Groq Vision API ───────────────────────────────────────────────────────────
def ask_groq_image(image_bytes, mime_type, user_caption, api_key):
    url     = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    b64     = base64.b64encode(image_bytes).decode("utf-8")
    instruction = user_caption.strip() or (
        "Analyze this image from a sustainability perspective. "
        "Identify environmental issues or opportunities and give practical eco-friendly advice."
    )
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {"role": "system", "content":
                "You are EcoWise AI, a sustainability coach. Analyze images for environmental "
                "relevance — waste, energy, water, pollution, or greener opportunities. "
                "Be friendly and practical. Give tips only when asked."},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                {"type": "text", "text": instruction}
            ]}
        ],
        "temperature": 0.7, "max_tokens": 600
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "⚠️ No internet connection. Please check your network and try again."
    except requests.exceptions.Timeout:
        return "⚠️ Image analysis timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        try:    err = r.json().get("error", {}).get("message", str(e))
        except: err = str(e)
        return f"⚠️ Image API error: {err}"
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ── Constants ─────────────────────────────────────────────────────────────────
TOPIC_COLORS = {
    "Water Conservation":     "#1565C0",
    "Energy Saving":          "#E65100",
    "Waste Management":       "#4E342E",
    "Climate Action":         "#1B5E20",
    "General Sustainability": "#6A1B9A",
    "Image Analysis":         "#00695C",
}
TOPIC_ICONS = {
    "Water Conservation":     "💧",
    "Energy Saving":          "⚡",
    "Waste Management":       "♻️",
    "Climate Action":         "🌍",
    "General Sustainability": "🌿",
    "Image Analysis":         "📷",
}
SPINNER_MESSAGES = {
    "Water Conservation":     "💧 Finding water saving tips...",
    "Energy Saving":          "⚡ Calculating energy solutions...",
    "Waste Management":       "♻️ Looking up waste management advice...",
    "Climate Action":         "🌍 Analyzing climate action steps...",
    "General Sustainability": "🌿 Thinking...",
}
QUICK_QUESTIONS = [
    ("💧", "How can I save water at home?"),
    ("⚡", "How to reduce electricity bill?"),
    ("♻️", "How to dispose e-waste?"),
    ("🌍", "How to reduce carbon footprint?"),
    ("🌧️", "Benefits of rainwater harvesting?"),
    ("🛍️", "How to reduce plastic waste?"),
]

# ── API Key ───────────────────────────────────────────────────────────────────
_env_key = os.getenv("GROQ_API_KEY", "")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌿 EcoWise AI")
    st.markdown("*Personal Sustainability Coach*")
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    if _env_key:
        api_key = _env_key
        st.success("✅ API Key loaded from environment")
    else:
        api_key = st.text_input("Groq API Key", type="password",
                                placeholder="gsk_xxxxxxxxxxxx",
                                help="Get your free key at groq.com")
        if not api_key:
            st.info("💡 Set GROQ_API_KEY as environment variable to skip this.")
    st.markdown("---")
    st.markdown("### 🗂 Topics Covered")
    for topic, icon in TOPIC_ICONS.items():
        if topic not in ("General Sustainability", "Image Analysis"):
            st.markdown(f"{icon} **{topic}**")
    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.update({"messages": [], "quick_question": "", "image_pending": None})
        st.rerun()
    st.markdown(
        '''<div class="sidebar-footer">
        🌿 EcoWise AI<br>
        SDG 6 · SDG 7 · SDG 12 · SDG 13<br>
        Powered by Groq + Prompt Engineering
        </div>''',
        unsafe_allow_html=True
    )

# ── Session State ─────────────────────────────────────────────────────────────
for key, val in [("messages", []), ("quick_question", ""), ("image_pending", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🌿 EcoWise AI")
st.markdown("**Your Personal Sustainability Coach** — Ask me anything about water, energy, waste, or climate!")
st.markdown("---")

# ── Welcome Card + Quick Questions (first time only) ─────────────────────────
if len(st.session_state["messages"]) == 0:

    # Welcome card
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
        border: 1px solid #66BB6A;
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        margin-bottom: 20px;
    ">
        <h3 style="color:#2E7D32; margin:0;">👋 Welcome to EcoWise AI!</h3>
        <p style="color:#555; margin-top:8px; font-size:14px;">
            I can help you with <b>Water Conservation</b>,
            <b>Energy Saving</b>, <b>Waste Management</b>
            and <b>Climate Action</b>.
        </p>
        <p style="color:#888; font-size:12px; margin-bottom:0;">
            💡 Click a quick question below or type your own!
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Quick questions
    st.markdown(
        "<p style='text-align:center;color:#2E7D32;font-size:15px;font-weight:600;'>"
        "✨ What would you like to know?</p>",
        unsafe_allow_html=True
    )
    col1, col2 = st.columns(2)
    for i, (emoji, q) in enumerate(QUICK_QUESTIONS):
        with (col1 if i % 2 == 0 else col2):
            if st.button(f"{emoji} {q}", use_container_width=True, key=f"qq_{i}"):
                st.session_state["quick_question"] = q
    st.markdown("---")

# ── Session Counter ───────────────────────────────────────────────────────────
if len(st.session_state["messages"]) > 0:
    count = len(st.session_state["messages"]) // 2
    st.markdown(
        f"<p style='text-align:right; font-size:11px; color:#9E9E9E;'>"
        f"💬 {count} question{'s' if count != 1 else ''} asked this session</p>",
        unsafe_allow_html=True
    )

# ── Chat History ──────────────────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        with st.chat_message("user"):
            if "image" in msg:
                st.image(msg["image"], width=260)
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🌿"):
            topic = msg.get("topic", "General Sustainability")
            color = TOPIC_COLORS.get(topic, "#2E7D32")
            icon  = TOPIC_ICONS.get(topic, "🌿")
            st.markdown(
                f'<span class="topic-badge" style="background:{color}22;'
                f'color:{color};border:1px solid {color}">{icon} {topic}</span>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'''<div style="
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 12px 16px;
                    margin-top: 6px;
                    font-size: 14px;
                    line-height: 1.7;
                ">{msg["content"]}</div>''',
                unsafe_allow_html=True
            )

# ── Image Pending Preview ─────────────────────────────────────────────────────
if st.session_state["image_pending"]:
    img = st.session_state["image_pending"]
    st.markdown(f"""
    <div style="
        background: #e8f5e9;
        border: 1px solid #66BB6A;
        border-radius: 12px;
        padding: 8px 14px;
        margin-bottom: 8px;
        font-size: 13px;
        color: #2E7D32;
    ">📷 &nbsp;<b>{img['name']}</b>&nbsp; ready to send</div>
    """, unsafe_allow_html=True)
    prev_col, rem_col = st.columns([1, 5])
    with prev_col:
        st.image(img["bytes"], width=80)
    with rem_col:
        if st.button("✕ Remove image", key="remove_img"):
            st.session_state["image_pending"] = None
            st.rerun()

# ── Chat Bar ──────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask a sustainability question... 🌱")

# ── Image Upload ──────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "📎 Attach an image (jpg, png, webp)",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="visible",
    key="img_uploader",
)
if uploaded and st.session_state["image_pending"] is None:
    st.session_state["image_pending"] = {
        "bytes":     uploaded.read(),
        "mime_type": uploaded.type,
        "name":      uploaded.name,
    }
    st.rerun()

# ── Resolve Question ──────────────────────────────────────────────────────────
if st.session_state["quick_question"]:
    question = st.session_state["quick_question"]
    st.session_state["quick_question"] = ""
else:
    question = user_input

# ── Process ───────────────────────────────────────────────────────────────────
if question:
    if not api_key:
        st.warning("⚠️ Please enter your Groq API key in the sidebar.")
    else:
        img_pending = st.session_state.get("image_pending")

        # ── Image + Question ──────────────────────────────────────────────────
        if img_pending:
            with st.chat_message("user"):
                st.image(img_pending["bytes"], width=260)
                st.markdown(question)
            st.session_state["messages"].append(
                {"role": "user", "content": question, "image": img_pending["bytes"]}
            )
            st.session_state["image_pending"] = None

            with st.chat_message("assistant", avatar="🌿"):
                with st.spinner("🔍 Analyzing image..."):
                    answer = ask_groq_image(
                        img_pending["bytes"], img_pending["mime_type"], question, api_key
                    )
                color = TOPIC_COLORS["Image Analysis"]
                st.markdown(
                    f'<span class="topic-badge" style="background:{color}22;'
                    f'color:{color};border:1px solid {color}">📷 Image Analysis</span>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'''<div style="
                        border-left: 4px solid {color};
                        border-radius: 8px;
                        padding: 12px 16px;
                        margin-top: 6px;
                        font-size: 14px;
                        line-height: 1.7;
                    ">{answer}</div>''',
                    unsafe_allow_html=True
                )
            st.session_state["messages"].append(
                {"role": "assistant", "content": answer, "topic": "Image Analysis"}
            )

        # ── Text Only ─────────────────────────────────────────────────────────
        else:
            with st.chat_message("user"):
                st.markdown(question)
            st.session_state["messages"].append({"role": "user", "content": question})

            topic = detect_topic(question)
            color = TOPIC_COLORS.get(topic, "#2E7D32")
            icon  = TOPIC_ICONS.get(topic, "🌿")
            chat_history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state["messages"]
            ]

            with st.chat_message("assistant", avatar="🌿"):
                with st.spinner(SPINNER_MESSAGES.get(topic, "🌱 Thinking...")):
                    answer = ask_groq(get_prompt(topic), chat_history, api_key)
                st.markdown(
                    f'<span class="topic-badge" style="background:{color}22;'
                    f'color:{color};border:1px solid {color}">{icon} {topic}</span>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'''<div style="
                        border-left: 4px solid {color};
                        border-radius: 8px;
                        padding: 12px 16px;
                        margin-top: 6px;
                        font-size: 14px;
                        line-height: 1.7;
                    ">{answer}</div>''',
                    unsafe_allow_html=True
                )
            st.session_state["messages"].append(
                {"role": "assistant", "content": answer, "topic": topic}
            )