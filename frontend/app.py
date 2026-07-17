import streamlit as st
import requests
import time
import uuid
import storage

st.set_page_config(page_title="MCA Compliance AI", page_icon="⚓", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-size: 18.5px; }
[data-testid="stAppViewContainer"] { background-color: #FFFFFF; }
[data-testid="stHeader"] { background-color: #FFFFFF; }
[data-testid="stSidebar"] { background-color: #F7F8FA; border-right: 1px solid #E5E7EB; }
[data-testid="stSidebar"] .stButton button {font-size: 0.85rem;}
[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) .stButton button {
    color: #9CA3AF;
    padding: 0.2rem 0.5rem;
    min-height: unset;
}
[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) .stButton button:hover {
    color: #DC2626;
    background-color: #FEF2F2;
}
[data-testid="stMainBlockContainer"] {max-width: 1600px;margin: 0 auto;padding-top: 2rem;}
[data-testid="stChatMessage"] {
    overflow: hidden;
    padding: 0.85rem 1rem !important;
}
.status-row {
    max-width: 100%;
    box-sizing: border-box;
    padding-right: 0.5rem;
}

.app-title { font-size: 1.55rem; font-weight: 700; color: #111827; margin-bottom: 0.1rem; }
.app-sub { color: #6B7280; font-size: 0.95rem; margin-bottom: 1.4rem; }

[data-testid="stChatMessage"] { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 0.4rem 0.2rem; }
[data-testid="stChatMessage"] p { font-size: 1.08rem; line-height: 1.75; }

.stChatInput textarea { border-radius: 10px !important; font-size: 1.08rem !important; }

.sidebar-conv {
    display: block; width: 100%; text-align: left; background: none; border: none;
    padding: 0.5rem 0.6rem; margin: 0.1rem 0; border-radius: 6px; color: #374151;
    font-size: 0.9rem; cursor: pointer;
}
.sidebar-conv:hover { background-color: #EEF2F6; }
.sidebar-heading { font-size: 0.78rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; margin: 1.2rem 0 0.4rem 0; }

.clause-chip {
    display: inline-flex; align-items: center; gap: 0.35rem; background-color: #F1F5F9;
    border: 1px solid #E2E8F0; border-radius: 999px; padding: 0.25rem 0.7rem;
    margin: 0.2rem 0.3rem 0.2rem 0; font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; color: #334155;
}
.clause-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }

.status-row { margin-top: 0.6rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.badge { font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 999px; }
.badge-cache { background-color: #EEF2FF; color: #4338CA; }
.badge-verified { background-color: #ECFDF5; color: #059669; }
.badge-unverified { background-color: #FEF2F2; color: #DC2626; }
.badge-time { background-color: #F8FAFC; color: #64748B; }

.low-confidence-note {
    background-color: #FFFBEB; border: 1px solid #FDE68A; color: #92400E;
    border-radius: 8px; padding: 0.6rem 0.9rem; font-size: 0.88rem; margin-top: 0.6rem;
}
.cited-text { font-size: 0.92rem; color: #4B5563; line-height: 1.6; margin-bottom: 0.7rem; }
.cited-label { font-family: 'IBM Plex Mono', monospace; font-weight: 600; color: #111827; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

def start_new_conversation():
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = []

def persist():
    if st.session_state.messages:
        title = st.session_state.messages[0]["content"][:45]
        storage.save_conversation(st.session_state.conversation_id, title, st.session_state.messages)

with st.sidebar:
    st.markdown('<div class="app-title">⚓ MCA Compliance AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub">SPVC 2025 — Beta reference tool</div>', unsafe_allow_html=True)
    if st.button("＋ New conversation", use_container_width=True):
        start_new_conversation()
        st.rerun()

    st.markdown('<div class="sidebar-heading">Recent conversations</div>', unsafe_allow_html=True)
    for conv in storage.list_conversations():
        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(conv["title"] or "Untitled", key=f"conv_{conv['id']}", use_container_width=True):
                st.session_state.conversation_id = conv["id"]
                st.session_state.messages = storage.load_conversation(conv["id"])
                st.rerun()
        with col2:
            if st.button("×", key=f"del_{conv['id']}"):
                storage.delete_conversation(conv["id"])
                if st.session_state.conversation_id == conv["id"]:
                    start_new_conversation()
                st.rerun()

    st.caption("Answers are generated from the Code and are not a substitute for advice from the MCA or a Certifying Authority.")

st.markdown('<div class="app-title">Ask about the Sport or Pleasure Vessel Code</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">Ask a question in plain English — every answer is cited against the Code.</div>', unsafe_allow_html=True)

def render_sources(sources):
    if not sources:
        return
    html = ""
    for s in sources:
        score = s["score"]
        color = "#059669" if score >= 0.6 else ("#D97706" if score >= 0.45 else "#DC2626")
        html += f'<span class="clause-chip"><span class="clause-dot" style="background-color:{color};"></span>{s["clause"]} · p.{s["page"]}</span>'
    st.markdown(html, unsafe_allow_html=True)

    with st.expander("View cited clause text"):
        for s in sources:
            st.markdown(f'<div class="cited-label">Clause {s["clause"]} — p.{s["page"]} (relevance {s["score"]:.2f})</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cited-text">{s["text"]}</div>', unsafe_allow_html=True)

def render_status(elapsed, from_cache, verified):
    badges = f'<span class="badge badge-time">{elapsed:.1f}s</span>'
    if from_cache:
        badges += '<span class="badge badge-cache">⚡ cached</span>'
    badges += '<span class="badge badge-verified">✓ verified</span>' if verified else '<span class="badge badge-unverified">⚠ unverified citation</span>'
    st.markdown(f'<div class="status-row">{badges}</div>', unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="⚓" if msg["role"] == "assistant" else None):
        st.write(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            render_sources(msg["sources"])
            if msg.get("top_score", 1) < 0.45:
                st.markdown('<div class="low-confidence-note">⚠ Weak match to the Code — verify with the MCA or a Certifying Authority.</div>', unsafe_allow_html=True)
            render_status(msg["elapsed"], msg["from_cache"], msg["verified"])

if not st.session_state.messages:
    st.markdown("<br>", unsafe_allow_html=True)
    examples = [
        "Do I need a kill cord on my rigid inflatable boat?",
        "How many liferafts do I need for 20 passengers in area category 1?",
        "Can I operate my vessel single-handed?",
    ]
    cols = st.columns(len(examples))
    for col, ex in zip(cols, examples):
        if col.button(ex, use_container_width=True):
            st.session_state.pending_question = ex
            st.rerun()

question = st.chat_input("Ask a question about the SPVC...")
if "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant", avatar="⚓"):
        with st.spinner("Searching the Code..."):
            start = time.perf_counter()
            try:
                response = requests.post(
                    "http://localhost:8000/ask",
                    json={"question": question},
                    timeout=120,
                )
                response.raise_for_status()
                result = response.json()
                elapsed = time.perf_counter() - start

                sources = result["sources"]
                top_score = sources[0]["score"] if sources else 0

                st.write(result["answer"])
                render_sources(sources)
                if top_score < 0.45:
                    st.markdown('<div class="low-confidence-note">⚠ Weak match to the Code — verify with the MCA or a Certifying Authority.</div>', unsafe_allow_html=True)
                render_status(elapsed, result["from_cache"], result["verified"])

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": sources,
                    "top_score": top_score,
                    "elapsed": elapsed,
                    "from_cache": result["from_cache"],
                    "verified": result["verified"],
                })
                persist()

            except requests.exceptions.RequestException as e:
                st.error(f"Something went wrong: {e}")