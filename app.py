"""MedMesh Sentinel — Clinical Glass Sky UI with Live n8n Workflow Animation."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agents.orchestrator import MedMeshDirector
from agents.workflow_viz import render_n8n_workflow

st.set_page_config(
    page_title="MedMesh Sentinel | Autonomous Pharmacovigilance",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

SAMPLES = {
    "High-Risk Anticoagulant Trio (Default)": {
        "drugs": "Warfarin, Aspirin, Omeprazole",
        "condition": "cardiovascular",
    },
    "CYP2C19 & Triple-Whammy Renal Check": {
        "drugs": "Clopidogrel, Omeprazole, Lisinopril, Ibuprofen",
        "condition": "hypertension",
    },
    "Statin + Macrolide & Diabetes Regimen": {
        "drugs": "Atorvastatin, Clarithromycin, Metformin, Furosemide",
        "condition": "hyperlipidemia",
    },
}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
code, pre, .mono { font-family: 'JetBrains Mono', monospace !important; }
.stApp { background: linear-gradient(155deg, #F0F7FF 0%, #F8FAFC 55%, #ECFEFF 100%); }
@keyframes slideIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.hero-med {
    animation: slideIn .4s ease-out;
    background: rgba(255,255,255,0.92);
    border: 1px solid #BAE6FD;
    border-left: 6px solid #0284C7;
    border-radius: 14px;
    padding: 1.05rem 1.35rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 10px 26px rgba(2,132,199,0.08);
}
.kpi-med {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 0.85rem 1rem;
    transition: transform .2s ease, border-color .2s ease;
    box-shadow: 0 4px 12px rgba(15,23,42,0.04);
}
.kpi-med:hover { transform: translateY(-2px); border-color: #0284C7; }
.kpi-l { color:#64748B; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:700; }
.kpi-v { color:#0F172A; font-size:1.38rem; font-weight:700; margin-top:0.15rem; }
.pill-high { background:#FFE4E6; color:#BE123C; border:1px solid #FB7185; padding:4px 12px; border-radius:999px; font-weight:700; font-size:0.78rem; }
.pill-mod { background:#FEF3C7; color:#B45309; border:1px solid #FBBF24; padding:4px 12px; border-radius:999px; font-weight:700; font-size:0.78rem; }
.pill-low { background:#CCFBF1; color:#0F766E; border:1px solid #2DD4BF; padding:4px 12px; border-radius:999px; font-weight:700; font-size:0.78rem; }
</style>
""",
    unsafe_allow_html=True,
)

if "med_drugs" not in st.session_state:
    s0 = SAMPLES["High-Risk Anticoagulant Trio (Default)"]
    st.session_state.med_drugs = s0["drugs"]
    st.session_state.med_cond = s0["condition"]


def _apply_sample() -> None:
    s = SAMPLES[st.session_state.med_sample]
    st.session_state.med_drugs = s["drugs"]
    st.session_state.med_cond = s["condition"]
    st.session_state.med_force = True


with st.sidebar:
    st.markdown("### Sample Regimens")
    st.selectbox("Load Clinical Regimen Preset", list(SAMPLES.keys()), key="med_sample", on_change=_apply_sample)
    st.markdown("### Regimen Control")
    drugs_raw = st.text_input("Drug List (comma-separated)", key="med_drugs")
    condition_in = st.text_input("ClinicalTrials Condition Filter", key="med_cond")

    with st.expander("AI Brain Keys (Optional)"):
        gemini_key = st.text_input("Gemini API Key Override", type="password", placeholder="Auto via Secrets / Env")
        groq_key = st.text_input("Groq API Key Override", type="password", placeholder="Auto-fallback")

    run_btn = st.button("Run Pharmacovigilance Mesh", type="primary", width="stretch")
    st.caption("Manoj Sapkal · BTCOC701 · Educational Only")

if "med_result" not in st.session_state or run_btn or st.session_state.pop("med_force", False):
    drugs_list = [d.strip() for d in drugs_raw.split(",") if d.strip()]
    with st.spinner("Querying OpenFDA FAERS, Labels, PubChem & ClinicalTrials.gov v2..."):
        st.session_state.med_result = MedMeshDirector().run_screening(
            drugs=drugs_list,
            condition=condition_in,
            gemini_key=gemini_key,
            groq_key=groq_key,
        )

res = st.session_state.med_result
triage = res["triage_level"]
pill_cls = "pill-high" if "HIGH" in triage else ("pill-mod" if "MODERATE" in triage else "pill-low")
msgs = res["messages"]

st.markdown(
    f"""
<div class="hero-med">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.6rem;">
    <div>
      <div style="font-size:1.6rem; font-weight:700; color:#0F172A;">MedMesh Sentinel — Clinical Pharmacovigilance</div>
      <div class="mono" style="color:#475569; font-size:0.82rem;">OpenFDA FAERS · Drug Labels · PubChem · ClinicalTrials.gov v2</div>
    </div>
    <div><span class="{pill_cls}">{triage} · {res['risk_score']}/100</span></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="kpi-med"><div class="kpi-l">Regimen Drugs</div><div class="kpi-v">{len(res["drugs"])}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-med"><div class="kpi-l">Interaction Pairs</div><div class="kpi-v">{len(res["pair_flags"])}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-med"><div class="kpi-l">Linked Trials</div><div class="kpi-v">{len(res["trials"])}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-med"><div class="kpi-l">AI Layer ({res["synthesis"]["latency_ms"]}ms)</div><div class="kpi-v" style="font-size:1.0rem;">{res["synthesis"]["model"]}</div></div>', unsafe_allow_html=True)

st.markdown("")
wf_nodes = [
    {"title": "MedMesh Director", "role": "Orchestrator", "phase": "TRIGGER", "metric": f"{len(res['drugs'])} drugs", "payload": f"Screening regimen {', '.join(res['drugs'])} for {condition_in}", "confidence": 0.98, "color": "#0284C7", "icon": "🏥"},
    {"title": "OpenFDASafetyScout", "role": "Scout 1", "phase": "SENSE", "metric": f"{len(res['drug_profiles'])} profiles", "payload": msgs[1]["content"] if len(msgs) > 1 else "Fetched FAERS & PubChem", "confidence": msgs[1]["confidence"] if len(msgs) > 1 else 0.94, "color": "#0D9488", "icon": "💊"},
    {"title": "InteractionGraph", "role": "Critic 1", "phase": "GRAPH", "metric": f"{len(res['pair_flags'])} flags", "payload": msgs[2]["content"] if len(msgs) > 2 else "Evaluated CYP/synergy pairs", "confidence": msgs[2]["confidence"] if len(msgs) > 2 else 0.93, "color": "#E11D48", "icon": "🔗"},
    {"title": "ClinicalTrialAgent", "role": "Scout 2", "phase": "TRIALS", "metric": f"{len(res['trials'])} NCTs", "payload": msgs[3]["content"] if len(msgs) > 3 else "Queried ClinicalTrials v2", "confidence": msgs[3]["confidence"] if len(msgs) > 3 else 0.90, "color": "#6366F1", "icon": "🧪"},
    {"title": "PolypharmacyTriage", "role": "Utility", "phase": "SCORE", "metric": f"{res['risk_score']}/100", "payload": msgs[4]["content"] if len(msgs) > 4 else triage, "confidence": msgs[4]["confidence"] if len(msgs) > 4 else 0.95, "color": "#D97706", "icon": "⚖️"},
    {"title": "PharmaMemory + UI", "role": "Persister", "phase": "SYNC", "metric": res["synthesis"]["provider"].split()[0], "payload": f"Saved {len(res['memory'].get('seen_trial_ncts', []))} NCT IDs ({res['memory'].get('total_screenings', 1)} runs)", "confidence": 0.97, "color": "#0284C7", "icon": "💾"},
]
render_n8n_workflow(
    wf_nodes,
    theme={"mode": "light", "bg": "#F4F9FF", "card_bg": "#FFFFFF", "border": "#BAE6FD", "accent": "#0284C7", "text": "#0F172A", "muted": "#475569", "bar_bg": "#EFF6FF", "dot": "#CBD5E1"},
    engine_label=f"MedMesh DAG · {res['synthesis']['provider']}",
)

t1, t2, t3 = st.tabs(["FAERS Volume & Risk Telemetry", "Interactions & Clinical Trials", "Agent Bus & Memory"])

with t1:
    g_l, g_r = st.columns([1, 1.35])
    with g_l:
        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=float(res["risk_score"]),
                title={"text": f"Polypharmacy Risk ({triage})", "font": {"size": 15, "color": "#0F172A"}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#E11D48" if res["risk_score"] >= 60 else ("#D97706" if res["risk_score"] >= 30 else "#0D9488")},
                    "steps": [
                        {"range": [0, 30], "color": "#CCFBF1"},
                        {"range": [30, 60], "color": "#FEF3C7"},
                        {"range": [60, 100], "color": "#FFE4E6"},
                    ],
                },
            )
        )
        gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=290, margin=dict(l=15, r=15, t=42, b=10))
        st.plotly_chart(gauge, width="stretch")

    prof_df = pd.DataFrame(res["drug_profiles"])
    with g_r:
        if not prof_df.empty:
            prof_df["warning_flag"] = prof_df["has_boxed_warning"].map(lambda x: "Boxed Warning" if x else "Standard Label")
            fig_faers = px.bar(
                prof_df,
                x="top_reaction_volume",
                y="drug",
                color="warning_flag",
                orientation="h",
                color_discrete_map={"Boxed Warning": "#E11D48", "Standard Label": "#0284C7"},
                title="OpenFDA FAERS Top-Reaction Volume by Drug",
                height=290,
            )
            fig_faers.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.65)", margin=dict(l=10, r=10, t=38, b=10))
            st.plotly_chart(fig_faers, width="stretch")

    if not prof_df.empty:
        max_vol = int(max(prof_df["top_reaction_volume"].max(), 10))
        st.dataframe(
            prof_df[["drug", "has_boxed_warning", "top_reaction_volume", "top_reactions", "formula", "molecular_weight", "source"]],
            width="stretch",
            hide_index=True,
            column_config={
                "has_boxed_warning": st.column_config.CheckboxColumn("Boxed Warn"),
                "top_reaction_volume": st.column_config.ProgressColumn("FAERS Vol", min_value=0, max_value=max_vol, format="%d"),
            },
        )

    with st.expander(f"AI Pharmacovigilance Brief ({res['synthesis']['provider']} · {res['synthesis']['model']})", expanded=False):
        st.write(res["synthesis"]["text"])

with t2:
    c_a, c_b = st.columns([1.05, 1.25])
    with c_a:
        st.markdown("#### Pairwise Synergy & CYP Conflicts")
        pf_df = pd.DataFrame(res["pair_flags"])
        if not pf_df.empty:
            fig_pf = px.bar(pf_df, x="severity_pts", y="pair", orientation="h", color="evidence", title="Pairwise Conflict Severity Points", height=240)
            fig_pf.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.7)", margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig_pf, width="stretch")
            st.dataframe(
                pf_df,
                width="stretch",
                hide_index=True,
                column_config={"severity_pts": st.column_config.ProgressColumn("Severity", min_value=0, max_value=50, format="%d pts")},
            )
        else:
            st.info("No major pairwise conflict rules triggered for this drug combination.")

    with c_b:
        st.markdown(f"#### ClinicalTrials.gov v2 Studies (`{condition_in}`)")
        tr_df = pd.DataFrame(res["trials"])
        if not tr_df.empty:
            st.dataframe(tr_df[["nct_id", "status", "phases", "title"]], width="stretch", hide_index=True)

with t3:
    msg_df = pd.DataFrame(msgs)
    if not msg_df.empty:
        fig_m = px.bar(msg_df, x="sender", y="confidence", color="phase", title="Sub-Agent Execution Confidence", height=240)
        fig_m.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.7)", margin=dict(l=10, r=10, t=35, b=10))
        st.plotly_chart(fig_m, width="stretch")
        st.dataframe(msg_df[["phase", "sender", "recipient", "confidence", "content"]], width="stretch", hide_index=True)

    hist = res["memory"].get("triage_history", [])
    if hist:
        h_df = pd.DataFrame(hist)
        st.plotly_chart(px.area(h_df, x="timestamp_utc", y="risk_score", markers=True, title="Persistent Triage Risk History", height=220), width="stretch")

    st.table(
        pd.DataFrame(
            [
                {"PEAS": "Performance", "Spec": "Interaction sensitivity, boxed-warning capture, triage accuracy"},
                {"PEAS": "Environment", "Spec": "OpenFDA FAERS/Labels, PubChem REST, ClinicalTrials.gov v2"},
                {"PEAS": "Actuators", "Spec": "Clinical Sky UI, Risk Gauge, state/pharma_memory.json"},
                {"PEAS": "Sensors", "Spec": "FAERS reaction counts, drug label text, NCT study phases"},
            ]
        )
    )
