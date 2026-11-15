"""MedMesh Sentinel — Clinical Glass Precision UI."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from agents.orchestrator import MedMeshDirector

st.set_page_config(
    page_title="MedMesh Sentinel | Autonomous Pharmacovigilance Agent",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: #0C4A6E; }
code, pre, .mono { font-family: 'IBM Plex Mono', monospace !important; }
.stApp { background: linear-gradient(155deg, #F0F9FF 0%, #E0F2FE 50%, #F8FAFC 100%); }
.clinical-hero {
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(3, 105, 161, 0.22);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.glass-tile {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid rgba(14, 165, 233, 0.2);
    border-radius: 12px;
    padding: 0.95rem 1.05rem;
}
.bus-pill {
    background: #FFFFFF;
    border-left: 4px solid #0D9488;
    border-radius: 0 10px 10px 0;
    padding: 0.7rem 1rem;
    margin-bottom: 0.55rem;
    box-shadow: 0 2px 6px rgba(12, 74, 110, 0.06);
}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Regimen Screening Input")
    drugs_text = st.text_input("Co-Administered Drugs (comma-separated)", value="Warfarin, Aspirin, Atorvastatin")
    condition_in = st.text_input("Clinical Focus / Condition", value="cardiovascular")
    with st.expander("AI Brain Keys (Optional — 90% Keyless)"):
        gemini_key = st.text_input("Gemini API Key Override", type="password")
        groq_key = st.text_input("Groq API Key Override", type="password")
    run_btn = st.button("Screen Regimen & Trials", type="primary", use_container_width=True)
    st.caption("Educational Decision-Support Only | Shreyash Gole — BTCOC701")

if "medmesh_res" not in st.session_state or run_btn:
    drugs_list = [d.strip() for d in drugs_text.split(",") if d.strip()]
    with st.spinner("MedMesh coordinating OpenFDA, PubChem & ClinicalTrials.gov v2 sub-agents..."):
        st.session_state.medmesh_res = MedMeshDirector().run_screening(
            drugs=drugs_list,
            condition=condition_in,
            gemini_key=gemini_key,
            groq_key=groq_key,
        )

res = st.session_state.medmesh_res
triage_color = "#E11D48" if "HIGH" in res["triage_level"] else ("#D97706" if "MODERATE" in res["triage_level"] else "#0D9488")

st.markdown(
    f"""
<div class="clinical-hero">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.8rem;">
    <div>
      <h2 style="margin:0; color:#0C4A6E;">MedMesh Sentinel — Pharmacovigilance &amp; Polypharmacy Triage</h2>
      <div style="color:#475569; margin-top:0.25rem;">Autonomous multi-agent fusion across OpenFDA FAERS, FDA Labels, PubChem &amp; ClinicalTrials.gov API v2</div>
    </div>
    <div class="mono" style="background:{triage_color}; color:#FFFFFF; padding:0.35rem 0.85rem; border-radius:999px; font-size:0.82rem; font-weight:600;">
      {res['triage_level']} · {res['risk_score']}/100
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Drugs Profiled", len(res["drug_profiles"]))
k2.metric("Pairwise Flags", len(res["pair_flags"]))
k3.metric("Live Trials Found", len(res["trials"]))
k4.metric("10% AI Synthesizer", res["synthesis"]["provider"])

t1, t2, t3 = st.tabs(["Safety Dossier & Trials", "Sub-Agent Clinical Bus", "PEAS & Watchlist Memory"])

with t1:
    c_left, c_right = st.columns([1.25, 1])
    with c_left:
        st.subheader("OpenFDA & PubChem Molecular Profile")
        prof_df = pd.DataFrame(res["drug_profiles"])
        if not prof_df.empty:
            fig = px.bar(
                prof_df,
                x="drug",
                y="top_reaction_volume",
                color="has_boxed_warning",
                color_discrete_map={True: "#E11D48", False: "#0369A1"},
                title="FAERS Top Adverse-Event Report Volume",
                height=270,
            )
            fig.update_layout(paper_bgcolor="rgba(255,255,255,0.6)", plot_bgcolor="#FFFFFF", margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(prof_df[["drug", "formula", "molecular_weight", "has_boxed_warning", "top_reactions"]], use_container_width=True, hide_index=True)

        st.subheader("Pairwise Interaction Graph Signals")
        if res["pair_flags"]:
            st.dataframe(pd.DataFrame(res["pair_flags"]), use_container_width=True, hide_index=True)
        else:
            st.success("No major pairwise conflict detected among the checked drugs.")

    with c_right:
        st.subheader("Clinical Safety Director Brief")
        st.info(res["synthesis"]["text"])
        st.subheader("Live ClinicalTrials.gov v2 Evidence")
        if res["trials"]:
            st.dataframe(pd.DataFrame(res["trials"]), use_container_width=True, hide_index=True)
        else:
            st.caption("No matching trials returned for this query.")

with t2:
    st.subheader("Inter-Agent Clinical Coordination Trace")
    for m in res["messages"]:
        st.markdown(
            f'<div class="bus-pill"><div class="mono" style="font-size:0.78rem; color:#0369A1;">[{m["phase"]}] {m["sender"]} → {m["recipient"]} (conf={m["confidence"]})</div><div style="margin-top:0.2rem;">{m["content"]}</div></div>',
            unsafe_allow_html=True,
        )

with t3:
    st.subheader("PEAS Specification")
    st.table(
        pd.DataFrame(
            [
                {"Component": "P — Performance Measure", "Description": "Interaction recall, zero missed boxed warnings, transparent uncertainty + medical disclaimer."},
                {"Component": "E — Environment", "Description": "OpenFDA FAERS/Label APIs, ClinicalTrials.gov v2, PubChem REST, Streamlit & GitHub Actions."},
                {"Component": "A — Actuators", "Description": "Polypharmacy risk gauge, clinical brief emitter, deduplicated trial NCT memory updater."},
                {"Component": "S — Sensors", "Description": "Regimen drug list, live FDA adverse events & label interactions, trial JSON, state/pharma_memory.json."},
            ]
        )
    )
    if res["memory"].get("triage_history"):
        st.dataframe(pd.DataFrame(res["memory"]["triage_history"]), use_container_width=True, hide_index=True)
