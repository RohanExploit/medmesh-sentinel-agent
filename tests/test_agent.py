"""Automated pytest suite for MedMesh Sentinel pharmacovigilance agent."""

from __future__ import annotations

from pathlib import Path

from agents.memory import PharmaMemoryStore
from agents.orchestrator import MedMeshDirector
from agents.subagents import InteractionGraphAgent, PharmaContext


def test_pharma_memory_deduplicates_ncts(tmp_path: Path) -> None:
    store = PharmaMemoryStore(tmp_path / "pharma.json")
    s1 = store.update_after_screening(["Warfarin", "Aspirin"], ["NCT1", "NCT2"], 60.0, "MODERATE", "ok")
    s2 = store.update_after_screening(["Warfarin", "Aspirin"], ["NCT2", "NCT3"], 62.0, "MODERATE", "ok2")
    assert s1["seen_trial_ncts"] == ["NCT1", "NCT2"]
    assert s2["seen_trial_ncts"] == ["NCT1", "NCT2", "NCT3"]


def test_interaction_graph_detects_bleeding_synergy() -> None:
    agent = InteractionGraphAgent()
    ctx = PharmaContext(
        drugs=["Warfarin", "Aspirin"],
        condition="cardiovascular",
        seen_ncts=set(),
        drug_profiles=[{"interaction_text": ""}, {"interaction_text": ""}],
    )
    agent.run(ctx)
    assert len(ctx.pair_flags) == 1
    assert "hemorrhage" in ctx.pair_flags[0]["mechanism"].lower()


def test_full_screening_mocked(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "agents.subagents.fetch_openfda_adverse_events",
        lambda d: {"drug": d, "top_reactions": ["Bleeding (100)"], "top_reaction_volume": 100, "source": "mock"},
    )
    monkeypatch.setattr(
        "agents.subagents.fetch_openfda_label_interactions",
        lambda d: {"drug": d, "interaction_text": "Caution with anticoagulants.", "has_boxed_warning": True, "boxed_excerpt": "Warning", "source": "mock"},
    )
    monkeypatch.setattr(
        "agents.subagents.fetch_pubchem_properties",
        lambda d: {"formula": "C19H16O4", "molecular_weight": "308.3", "source": "mock"},
    )
    monkeypatch.setattr(
        "agents.subagents.fetch_clinical_trials",
        lambda q, limit=5: {"studies": [{"nct_id": "NCT001", "title": "Anticoagulant Trial", "status": "RECRUITING", "phases": "PHASE3"}], "source": "mock"},
    )
    out = MedMeshDirector(PharmaMemoryStore(tmp_path / "pharma.json")).run_screening(["Warfarin", "Aspirin"], gemini_key="", groq_key="")
    assert out["risk_score"] >= 65.0
    assert len(out["messages"]) == 5
