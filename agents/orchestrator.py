"""Lead MedMesh Clinical Safety Director orchestrating 4 pharmacovigilance sub-agents."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .llm_router import SynthesisResult, synthesize_with_fallback
from .memory import PharmaMemoryStore
from .subagents import (
    ClinicalTrialEvidenceAgent,
    InteractionGraphAgent,
    OpenFDASafetyScoutAgent,
    PharmaContext,
    PolypharmacyRiskTriageAgent,
)


def _universal_pharma_fallback(ctx: PharmaContext) -> str:
    top_flag = ctx.pair_flags[0] if ctx.pair_flags else None
    flag_text = f"{top_flag['pair']} — {top_flag['mechanism']}" if top_flag else "No high-severity pairwise rule conflict detected in checked regimen."
    return (
        f"### MedMesh Pharmacovigilance Triage ({ctx.triage_level} · {ctx.risk_score}/100)\n"
        f"- **Regimen Screened**: {', '.join(d.title() for d in ctx.drugs)} (OpenFDA FAERS + Labels + PubChem).\n"
        f"- **Primary Interaction Signal**: {flag_text}\n"
        f"- **Clinical Trials Context**: Linked {len(ctx.trials)} live ClinicalTrials.gov v2 studies.\n"
        f"- *Disclaimer: Educational AI decision-support only — never alter prescribed medication without a licensed physician/pharmacist.*"
    )


class MedMeshDirector:
    """Goal-Based + Model-Based + Utility-Based Pharmacovigilance Agent."""

    def __init__(self, memory_store: PharmaMemoryStore | None = None) -> None:
        self.memory = memory_store or PharmaMemoryStore()
        self.subagents = [
            OpenFDASafetyScoutAgent(),
            InteractionGraphAgent(),
            ClinicalTrialEvidenceAgent(),
            PolypharmacyRiskTriageAgent(),
        ]

    def run_screening(
        self,
        drugs: list[str],
        condition: str = "cardiovascular",
        gemini_key: str | None = None,
        groq_key: str | None = None,
    ) -> dict[str, Any]:
        clean_drugs = [d.strip() for d in drugs if d.strip()] or ["Warfarin", "Aspirin", "Omeprazole"]
        state = self.memory.load()
        ctx = PharmaContext(drugs=clean_drugs, condition=condition, seen_ncts=set(state.get("seen_trial_ncts", [])))
        ctx.emit(
            "MedMesh Director",
            "OpenFDASafetyScoutAgent",
            "DELEGATE",
            f"Dispatching autonomous OpenFDA + PubChem + ClinicalTrials.gov screening for {len(clean_drugs)} drugs.",
            confidence=0.98,
        )

        for agent in self.subagents:
            agent.run(ctx)

        prompt = (
            f"You are MedMesh Clinical Safety Director. Summarize this polypharmacy safety check in 3 crisp educational bullets "
            f"(Interaction Signal, FDA/FAERS Context, Pharmacist Verification Focus) under 115 words. Include non-prescriptive disclaimer.\n"
            f"Drugs: {clean_drugs}\nPair Flags: {ctx.pair_flags}\nRisk Score: {ctx.risk_score}"
        )
        synthesis: SynthesisResult = synthesize_with_fallback(
            prompt=prompt,
            system_instruction="Be medically cautious, factual, and always state educational-only disclaimer.",
            universal_fallback_fn=lambda: _universal_pharma_fallback(ctx),
            gemini_key=gemini_key,
            groq_key=groq_key,
        )

        updated_state = self.memory.update_after_screening(
            regimen=clean_drugs,
            nct_ids=[t["nct_id"] for t in ctx.trials],
            risk_score=ctx.risk_score,
            triage_level=ctx.triage_level,
            summary=synthesis.text,
        )

        return {
            "drugs": clean_drugs,
            "drug_profiles": ctx.drug_profiles,
            "pair_flags": ctx.pair_flags,
            "trials": ctx.trials,
            "risk_score": ctx.risk_score,
            "triage_level": ctx.triage_level,
            "messages": [asdict(m) for m in ctx.messages],
            "synthesis": asdict(synthesis),
            "memory": updated_state,
        }
