"""Streamlit UI for the Technical Documentation Assistant.

Talks to the FastAPI backend over HTTP — run the API first:
    uvicorn src.main:app --reload
then, in a second terminal:
    streamlit run app.py
"""
import requests
import streamlit as st

st.set_page_config(page_title="Tech Docs Assistant", page_icon="📚", layout="wide")

if "api_base" not in st.session_state:
    st.session_state.api_base = "http://localhost:8000"
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: question, answer, sources, query_type, retries_used, gave_up


def api_get(path: str, **kwargs):
    return requests.get(f"{st.session_state.api_base}{path}", timeout=60, **kwargs)


def api_post(path: str, **kwargs):
    return requests.post(f"{st.session_state.api_base}{path}", timeout=120, **kwargs)


# ---------- sidebar ----------

with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.api_base = st.text_input("API base URL", value=st.session_state.api_base)

    if st.button("Check connection", use_container_width=True):
        try:
            r = api_get("/health")
            if r.ok:
                st.success("Connected ✓")
            else:
                st.error(f"API returned {r.status_code}")
        except requests.RequestException as e:
            st.error(f"Can't reach API: {e}")

    st.divider()
    st.header("📄 Indexed Documents")
    try:
        docs = api_get("/documents").json().get("indexed_sources", [])
        if docs:
            for d in docs:
                st.markdown(f"- `{d}`")
        else:
            st.caption("No documents indexed yet.")
    except requests.RequestException:
        st.caption("Couldn't reach the API to list documents.")

    if st.button("🔄 Refresh document list", use_container_width=True):
        st.rerun()

    st.divider()
    st.header("⬆️ Ingest Documents")
    uploaded = st.file_uploader(
        "Upload .md / .txt files", type=["md", "txt"], accept_multiple_files=True
    )
    if st.button("Ingest uploaded files", use_container_width=True, disabled=not uploaded):
        files = [(f.name, f.getvalue(), "text/markdown") for f in uploaded]
        try:
            r = api_post("/ingest", files=[("files", (name, content, mime)) for name, content, mime in files])
            if r.ok:
                data = r.json()
                st.success(f"Ingested {len(data['ingested_files'])} file(s), {data['chunks_added']} chunks.")
                st.rerun()
            else:
                st.error(f"Ingest failed: {r.text}")
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")

    st.caption("No files selected → clicking below re-ingests the local `data/docs/` corpus.")
    if st.button("Re-ingest local data/docs/", use_container_width=True):
        try:
            r = api_post("/ingest")
            if r.ok:
                data = r.json()
                st.success(f"Ingested {len(data['ingested_files'])} file(s), {data['chunks_added']} chunks.")
                st.rerun()
            else:
                st.error(f"Ingest failed: {r.text}")
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")


# ---------- main ----------

st.title("📚 Technical Documentation Assistant")
st.caption("Self-corrective RAG over your docs — retrieval → grading → generation, with automatic query rewriting on failure.")

question = st.chat_input("Ask a question about the indexed documentation…")

if question:
    with st.spinner("Retrieving, grading, and generating…"):
        try:
            r = api_post("/query", json={"question": question})
            if r.ok:
                st.session_state.history.append(r.json())
            else:
                st.session_state.history.append(
                    {
                        "question": question,
                        "answer": f"⚠️ API error ({r.status_code}): {r.text}",
                        "sources": [],
                        "query_type": None,
                        "retries_used": 0,
                        "gave_up": True,
                    }
                )
        except requests.RequestException as e:
            st.session_state.history.append(
                {
                    "question": question,
                    "answer": f"⚠️ Couldn't reach the API: {e}",
                    "sources": [],
                    "query_type": None,
                    "retries_used": 0,
                    "gave_up": True,
                }
            )

# render conversation, most recent last
for i, turn in enumerate(st.session_state.history):
    with st.chat_message("user"):
        st.markdown(turn["question"])

    with st.chat_message("assistant"):
        st.markdown(turn["answer"])

        badges = []
        if turn.get("query_type"):
            badges.append(f"`{turn['query_type']}`")
        if turn.get("retries_used"):
            badges.append(f"🔁 {turn['retries_used']} retry(ies)")
        if turn.get("gave_up"):
            badges.append("❓ no confident answer")
        if badges:
            st.caption(" · ".join(badges))

        if turn.get("sources"):
            st.markdown("**Sources:** " + ", ".join(f"`{s}`" for s in turn["sources"]))

        col1, col2, _ = st.columns([1, 1, 8])
        with col1:
            if st.button("👍", key=f"up_{i}"):
                api_post(
                    "/feedback",
                    json={"question": turn["question"], "answer": turn["answer"], "rating": "up"},
                )
                st.toast("Thanks for the feedback!")
        with col2:
            if st.button("👎", key=f"down_{i}"):
                api_post(
                    "/feedback",
                    json={"question": turn["question"], "answer": turn["answer"], "rating": "down"},
                )
                st.toast("Thanks — noted.")

if not st.session_state.history:
    st.info("Ask something like *\"How do I share a dependency across multiple routes?\"* to get started.")
