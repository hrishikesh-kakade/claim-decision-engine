"""Streamlit reviewer UI for the Policy-Aware Multi-Agent RAG Claim Decision Engine.

Run:
    streamlit run frontend/streamlit_app.py

Configure the backend location with the CLAIM_API_URL environment variable
(defaults to http://localhost:8000). The UI never talks to the LLM or the
policy index directly -- it only calls the deployed /analyze API, so the
frontend and backend can be deployed and scaled independently.

Design goal: a reviewer with no technical background should be able to
look at this page for 10 seconds and know (a) what the decision was,
(b) exactly why, in one sentence each, and (c) how much is payable --
before ever needing to open a tab or read a citation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests
import streamlit as st

API_URL = st.secrets.get(
    "CLAIM_API_URL", 
    os.getenv("CLAIM_API_URL", "https://claim-decision-engine-production-8083.up.railway.app")
)
ROOT = Path(__file__).resolve().parent.parent

st.set_page_config(page_title="Claim Decision Engine", layout="wide")

# Decision status -> (emoji, color, one-line plain-English label)
DECISION_STYLE = {
    "ADMISSIBLE":              ("✅", "green",  "Approved — full amount payable"),
    "ADMISSIBLE_WITH_LIMITS":  ("✅", "blue",   "Approved — reduced by policy limits"),
    "PARTIALLY_ADMISSIBLE":    ("⚠️", "orange", "Partly approved — part of the claim is excluded"),
    "NOT_ADMISSIBLE":          ("❌", "red",    "Rejected"),
    "NEEDS_REVIEW":            ("🔍", "gray",   "Cannot decide yet — needs human review"),
}

st.title("Policy-Aware Multi-Agent RAG Claim Decision Engine")
st.caption(f"Backend: {API_URL}  ·  Policy: USGIC – CSC Individual Health Insurance (UNIHLIP18004V011718)")


# --------------------------------------------------------------------- LLM status banner
def _render_llm_status():
    """Always visible, regardless of whether a claim has been analyzed yet,
    so a reviewer can immediately see whether responses will use an LLM for
    narration or are pure rule-engine output -- and which provider, if any."""
    try:
        status = requests.get(f"{API_URL}/llm-status", timeout=5).json()
    except Exception as e:
        st.error(f"Could not reach backend to check LLM status: {e}")
        return
    provider = status.get("provider", "none")
    if provider == "none" or not status.get("available"):
        st.info(
            "🔌 **LLM: None** — running in pure rule-engine mode. "
            "Every sentence below is written by the deterministic Coverage & Exclusion Agent; "
            "no external AI call is made."
        )
    else:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.success(
                f" **LLM configured: `{provider}`** — used *only* to rephrase already-computed "
                f"findings for readability. It never decides the outcome or touches any number."
            )
        with col2:
            if st.button("Test connection"):
                test = requests.get(f"{API_URL}/llm-status?test=true", timeout=30).json()
                tc = test.get("test_call", {})
                if tc.get("succeeded"):
                    st.success(f"✅ Reached `{tc.get('provider')}` / `{tc.get('model')}`")
                else:
                    st.error(f"❌ Call failed: {tc.get('error')}")


_render_llm_status()


@st.cache_data(show_spinner=False)
def load_public_cases():
    path = ROOT / "data" / "public_test_cases.json"
    return json.loads(path.read_text()) if path.exists() else []


@st.cache_data(show_spinner=False)
def load_custom_cases():
    path = ROOT / "eval" / "cases" / "custom_cases.json"
    return json.loads(path.read_text()) if path.exists() else []


def call_api(payload: dict) -> dict:
    r = requests.post(f"{API_URL}/analyze", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------- Sidebar Setup

st.sidebar.header("1. Pick a claim case")
all_cases = {c["case_id"]: c for c in load_public_cases() + load_custom_cases()}


if "uploader_version" not in st.session_state:
    st.session_state["uploader_version"] = 0


def clear_analysis():
    """Safely clears old analysis results."""
    if "analysis_result" in st.session_state:
        del st.session_state["analysis_result"]


def on_file_uploaded():
    """Triggered when a file is uploaded — clears pasted text safely."""
    clear_analysis()
    # It is safe to assign to a text area string state
    st.session_state["pasted_json_input"] = ""


def on_text_pasted():
    """Triggered when text is pasted — resets file uploader by changing its key version."""
    clear_analysis()
    if st.session_state.get("pasted_json_input"):
        # Incrementing the key version forces Streamlit to create a fresh, empty file uploader
        st.session_state["uploader_version"] += 1


mode = st.sidebar.radio(
    "Input method",
    ["Pick a sample case", "Paste / upload JSON"],
    on_change=clear_analysis,
)

case_payload = None

if mode == "Pick a sample case":
    if all_cases:
        cid = st.sidebar.selectbox(
            "Case",
            list(all_cases.keys()),
            key="selected_case_id",
            on_change=clear_analysis,
        )
        case_payload = all_cases[cid]
        with st.sidebar.expander("View raw case JSON"):
            st.json(case_payload, expanded=False)
    else:
        st.sidebar.warning("No sample cases found under data/ or eval/cases/.")

else:
    # Use a dynamic key so changing the version re-renders an empty file uploader safely
    dynamic_uploader_key = f"file_uploader_{st.session_state['uploader_version']}"

    uploaded = st.sidebar.file_uploader(
        "Upload a claim case JSON",
        type=["json"],
        key=dynamic_uploader_key,
        on_change=on_file_uploaded,
    )

    pasted = st.sidebar.text_area(
        "...or paste JSON here",
        height=200,
        key="pasted_json_input",
        on_change=on_text_pasted,
    )

    # Route payload cleanly
    if uploaded is not None:
        try:
            case_payload = json.loads(uploaded.read())
        except Exception as e:
            st.sidebar.error(f"Invalid uploaded JSON file: {e}")
    elif pasted.strip():
        try:
            case_payload = json.loads(pasted)
        except json.JSONDecodeError as e:
            st.sidebar.error(f"Invalid JSON in text area: {e}")

st.sidebar.header("2. Analyze")
analyze_clicked = st.sidebar.button(
    "Analyze claim",
    type="primary",
    disabled=case_payload is None,
    use_container_width=True,
)

with st.sidebar.expander("Backend health"):
    try:
        h = requests.get(f"{API_URL}/health", timeout=5).json()
        st.success(h)
    except Exception as e:
        st.error(f"Backend unreachable: {e}")

if analyze_clicked and case_payload is not None:
    with st.spinner("Running the multi-agent pipeline..."):
        try:
            st.session_state["analysis_result"] = call_api(case_payload)
        except requests.HTTPError as e:
            st.error(f"API error: {e.response.status_code} - {e.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"Request failed: {e}")
            st.stop()

# Retrieve stored result
result = st.session_state.get("analysis_result")

# If no analysis has been run yet, show initial state and stop
if result is None:
    st.info("👈 Pick or paste a claim case in the sidebar, then click **Analyze claim**.")
    st.stop()

# ======================================================================= HEADLINE
decision = result["decision"]
emoji, color, plain_label = DECISION_STYLE.get(decision, ("❓", "gray", decision))
payable = result.get("payable_estimate_inr")

st.divider()
h1, h2, h3 = st.columns([3, 1, 1])
with h1:
    st.markdown(f"## {emoji} :{color}[{plain_label}]")
    st.caption(f"System status code: `{decision}`")
with h2:
    st.metric("Confidence", f"{result['confidence']:.0%}")
with h3:
    st.metric("Payable amount", f"₹{payable:,.0f}" if payable is not None else "Not determined")

# ======================================================================= WHY (the core ask)
# This is the single most important section on the page: a reviewer must be
# able to see, without digging into any tab, exactly why the system reached
# this decision. decision_reasons is always the rule engine's own exact
# wording, so it never gets muddled by LLM rephrasing.
reasons = result.get("decision_reasons") or []

st.markdown("### Why")

if decision == "NOT_ADMISSIBLE":
    st.error("**This claim is rejected because:**")
    for r in reasons:
        st.markdown(f"- {r}")
    st.caption("No amount is payable. See the Citations tab below for the exact policy clause(s) this is based on.")

elif decision == "PARTIALLY_ADMISSIBLE":
    st.warning("**Part of this claim is not payable, because:**")
    for r in reasons:
        st.markdown(f"- {r}")
    st.caption(f"The rest of the claim is admissible. Estimated payable amount: ₹{payable:,.0f}" if payable is not None else "")

elif decision == "ADMISSIBLE_WITH_LIMITS":
    st.info("**Approved, but the payable amount was reduced by standard policy limits:**")
    for r in reasons:
        st.markdown(f"- {r}")
    st.caption("Everything not listed above was fully payable as claimed.")

elif decision == "ADMISSIBLE":
    st.success("**Approved in full:**")
    for r in reasons:
        st.markdown(f"- {r}")

elif decision == "NEEDS_REVIEW":
    st.warning(
        "**The system is abstaining** — it will not guess. A safe, confident decision cannot be "
        "made yet, because:"
    )
    for r in reasons:
        st.markdown(f"- {r}")
    missing = result.get("missing_evidence") or []
    if missing:
        st.markdown("**What's needed to resolve this:**")
        for m in missing:
            st.markdown(f"- {m}")

else:
    for r in reasons:
        st.markdown(f"- {r}")

st.divider()

# ======================================================================= DETAILS (everything else)
tabs = st.tabs(["All Findings", "Applicable Limits", "Citations", "Execution Trace", "Raw JSON"])

with tabs[0]:
    st.caption("Every decision dimension the system checked for this case — not just the ones that mattered for the final outcome (those are in the 'Why' section above).")
    if result["key_findings"]:
        for f in result["key_findings"]:
            st.markdown(f"- {f}")
    else:
        st.write("No findings.")

with tabs[1]:
    limits = result.get("applicable_limits") or []
    if limits:
        st.caption("Category-by-category breakdown of claimed vs. payable amounts.")
        st.table([
            {
                "Limit": li["limit_name"],
                "Cap (INR)": f"{li['cap_inr']:,.0f}" if li.get("cap_inr") is not None else "—",
                "Claimed (INR)": f"{li['claimed_inr']:,.0f}",
                "Payable (INR)": f"{li['payable_inr']:,.0f}",
            }
            for li in limits
        ])
    else:
        st.write("No category sub-limits were applicable to this claim.")

def format_chunk_text(text: str) -> str:
    """Cleans raw PDF text by preserving bullet points and adding readable line breaks."""
    if not text:
        return ""
    # Ensure bullet points start on clean lines
    text = text.replace("", "\n- ").replace("•", "\n- ")
    # Ensure numbered list items start on new lines
    import re
    text = re.sub(r'(\b[i|v|x]+\b\))', r'\n  - \1', text) # format roman numerals (i), ii), etc.)
    return text

with tabs[2]:
    citations = result.get("citations") or []
    if citations:
        st.caption("Every material statement above is backed by one of these policy clauses — the **Result** column shows whether that clause counted for or against the claim.")
        VERDICT_LABEL = {
            "favorable": "✅ Passed (supports approval)",
            "unfavorable": "❌ Failed (supports rejection)",
            "uncertain": "🔍 Uncertain (evidence gap)",
            "neutral": "➖ Limit applied (routine)",
        }
        st.table([
            {
                "Result": VERDICT_LABEL.get(c.get("finding_verdict"), "—"),
                "Claim": c["claim"],
                "Section": c["section"],
                "Subsection": c.get("subsection") or "",
                "Page": c["page"],
                "Chunk ID": c["chunk_id"],
            }
            for c in citations
        ])
        
        with st.expander("Inspect a cited policy chunk", expanded=True):
            chunk_id = st.selectbox(
                "Chunk", 
                sorted({c["chunk_id"] for c in citations}),
                key="tab_citation_chunk_select"
            )
            if chunk_id:
                try:
                    chunk = requests.get(f"{API_URL}/policy/chunks/{chunk_id}", timeout=10).json()
                    
                    # Section Header
                    sec = chunk.get("section", "")
                    subsec = chunk.get("subsection") or ""
                    page = chunk.get("page_start") or chunk.get("page", "N/A")
                    st.markdown(f"#### 📄 {sec} {f'/ {subsec}' if subsec else ''} *(Page {page})*")
                    
                    # Formatted Readable Content Box
                    formatted_text = format_chunk_text(chunk.get("text", ""))
                    st.info(formatted_text)
                    
                except Exception as e:
                    st.error(f"Could not fetch chunk: {e}")
    else:
        st.write("No citations returned.")

with tabs[3]:
    st.caption("What each agent did, in order, with timing. No hidden reasoning — this is the full trace.")
    trace = result.get("trace") or []
    for step in trace:
        with st.container(border=True):
            cols = st.columns([2, 3, 1, 1])
            cols[0].markdown(f"**{step['agent']}**")
            cols[1].write(step.get("detail", ""))
            cols[2].write(f"n={step['retrieval_count']}" if step.get("retrieval_count") is not None else "")
            cols[3].write(f"{step['elapsed_ms']:.1f} ms" if step.get("elapsed_ms") is not None else "")

    v = result.get("validation", {})
    v_ok = v.get("status") == "PASS"
    st.markdown(("✅ " if v_ok else "❌ ") + f"**Validation:** `{v.get('status')}`" + (f" — {v.get('notes')}" if v.get("notes") else ""))
    if v.get("unsupported_claims"):
        for u in v["unsupported_claims"]:
            st.markdown(f"- ❌ {u}")

    llm = result.get("llm_narration") or {}
    if llm.get("succeeded"):
        st.markdown(f"**LLM narration for this request:** ✅ used `{llm.get('provider')}` / `{llm.get('model')}`")
    elif llm.get("called"):
        st.markdown(f"**LLM narration for this request:** ⚠️ attempted (`{llm.get('provider')}`) but failed — {llm.get('error')}. Deterministic findings shown above.")
    else:
        st.markdown(f"**LLM narration for this request:** ⬜ not used ({llm.get('error') or 'no provider configured'}). Deterministic findings shown above.")

with tabs[4]:
    st.json(result)
