import streamlit as st
import os
import requests
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
    .stChatInput > div > div > input {
        border: 2px solid #66BB6A;
        border-radius: 10px;
    }
    .topic-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ── Topic Detection ───────────────────────────────────────────────────────────


def detect_topic(question: str) -> str:
    q = question.lower()
    water_keywords = ["water", "rain", "tap", "irrigation", "river", "drink",
                      "shower", "leak", "groundwater", "harvest", "drought"]
    energy_keywords = ["energy", "electricity", "solar", "led", "power", "light",
                       "bulb", "battery", "appliance", "renewable", "wind", "bill"]
    waste_keywords = ["waste", "recycle", "plastic", "garbage", "trash", "compost",
                      "e-waste", "ewaste", "landfill", "dispose", "packaging", "pollution"]
    climate_keywords = ["climate", "carbon", "footprint", "global warming", "emission",
                        "co2", "greenhouse", "temperature", "sustainable", "environment"]
    scores = {
        "Water Conservation": sum(1 for k in water_keywords if k in q),
        "Energy Saving":      sum(1 for k in energy_keywords if k in q),
        "Waste Management":   sum(1 for k in waste_keywords if k in q),
        "Climate Action":     sum(1 for k in climate_keywords if k in q),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General Sustainability"

# ── Groq API Call ─────────────────────────────────────────────────────────────


def ask_groq(system_prompt: str, chat_history: list, api_key: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Build messages: system prompt + full chat history
    messages = [{"role": "system", "content": system_prompt}] + chat_history

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 600
    }
    try:
        response = requests.post(url, headers=headers,
                                 json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            return "⚠️ Invalid API key. Please check your Groq API key."
        try:
            err_detail = response.json().get("error", {}).get("message", str(e))
        except Exception:
            err_detail = str(e)
        return f"⚠️ API error: {err_detail}"
    except Exception as e:
        return f"⚠️ Something went wrong: {str(e)}"


# ── Constants ─────────────────────────────────────────────────────────────────
TOPIC_COLORS = {
    "Water Conservation":     "#1565C0",
    "Energy Saving":          "#E65100",
    "Waste Management":       "#4E342E",
    "Climate Action":         "#1B5E20",
    "General Sustainability": "#6A1B9A",
}
TOPIC_ICONS = {
    "Water Conservation":     "💧",
    "Energy Saving":          "⚡",
    "Waste Management":       "♻️",
    "Climate Action":         "🌍",
    "General Sustainability": "🌿",
}

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
        if topic != "General Sustainability":
            st.markdown(f"{icon} **{topic}**")

    st.markdown("---")

    # Example questions as quick buttons
    st.markdown("### ⚡ Quick Questions")
    examples = [
        "How can I save water at home?",
        "How to reduce electricity bill?",
        "How to dispose e-waste?",
        "How to reduce carbon footprint?",
        "Benefits of rainwater harvesting?",
        "How to reduce plastic waste?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["quick_question"] = ex

    st.markdown("---")

    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["quick_question"] = ""
        st.rerun()

    st.caption("🌱 Built with Python + Streamlit + Groq")

# ── Initialize Chat History ───────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "quick_question" not in st.session_state:
    st.session_state["quick_question"] = ""

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🌿 EcoWise AI")
st.markdown(
    "**Your Personal Sustainability Coach** — Ask me anything about water, energy, waste, or climate!")
st.markdown("---")

# ── Display Full Chat History ─────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🌿"):
            # Show topic badge if stored
            if "topic" in msg:
                topic = msg["topic"]
                icon = TOPIC_ICONS.get(topic, "🌿")
                color = TOPIC_COLORS.get(topic, "#2E7D32")
                st.markdown(
                    f'<span class="topic-badge" style="background:{color}22;'
                    f'color:{color};border:1px solid {color}">'
                    f'{icon} {topic}</span>',
                    unsafe_allow_html=True
                )
            st.markdown(msg["content"])

# ── Handle Quick Question from Sidebar ───────────────────────────────────────
if st.session_state["quick_question"]:
    prompt = st.session_state["quick_question"]
    st.session_state["quick_question"] = ""  # reset immediately
else:
    prompt = None

# ── Chat Input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask a sustainability question... 🌱")

# Use either chat input or quick question button
question = user_input or prompt

if question:
    if not api_key:
        st.warning("⚠️ Please enter your Groq API key in the sidebar.")
    else:
        # Show user message
        with st.chat_message("user"):
            st.markdown(question)

        # Add to history
        st.session_state["messages"].append(
            {"role": "user", "content": question})

        # Detect topic
        topic = detect_topic(question)
        icon = TOPIC_ICONS.get(topic, "🌿")
        color = TOPIC_COLORS.get(topic, "#2E7D32")

        # Get system prompt for this topic
        system_prompt = get_prompt(topic)

        # Build chat history for API (only role + content)
        chat_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state["messages"]
        ]

        # Get AI response
        with st.chat_message("assistant", avatar="🌿"):
            with st.spinner("🌱 Thinking..."):
                answer = ask_groq(system_prompt, chat_history, api_key)

            # Show topic badge
            st.markdown(
                f'<span class="topic-badge" style="background:{color}22;'
                f'color:{color};border:1px solid {color}">'
                f'{icon} {topic}</span>',
                unsafe_allow_html=True
            )
            st.markdown(answer)

        # Save assistant message with topic
        st.session_state["messages"].append({
            "role":    "assistant",
            "content": answer,
            "topic":   topic
        })

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center><small>🌿 EcoWise AI | SDG 6 · SDG 7 · SDG 12 · SDG 13 | "
    "Powered by Groq (Llama 3) + Prompt Engineering</small></center>",
    unsafe_allow_html=True
)
