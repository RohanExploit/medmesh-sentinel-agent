"""Four specialized Pharmacovigilance Sub-Agents under MedMesh Clinical Safety Director."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .tools import (
    fetch_clinical_trials,
    fetch_openfda_adverse_events,
    fetch_openfda_label_interactions,
    fetch_pubchem_properties,
)

KNOWN_PAIR_SYNERGIES: dict[tuple[str, str], tuple[str, int]] = {
    ("aspirin", "warfarin"): ("Elevated GI/intracranial hemorrhage synergy (antiplatelet + anticoagulant)", 38),
    ("ibuprofen", "warfarin"): ("NSAID-anticoagulant bleeding & INR elevation risk", 34),
    ("clopidogrel", "omeprazole"): ("CYP2C19 inhibition reduces clopidogrel bioactivation", 28),
    ("atorvastatin", "clarithromycin"): ("CYP3A4 inhibition increases statin myopathy/rhabdomyolysis risk", 30),
    ("lisinopril", "ibuprofen"): ("Triple-whammy acute kidney injury / blunted antihypertensive effect", 22),
    ("metformin", "furosemide"): ("Altered renal clearance; monitor lactic acidosis & glucose", 16),
}


@dataclass
class PharmaBusMessage:
    sender: str
    recipient: str
    phase: str
    content: str
    confidence: float


@dataclass
class PharmaContext:
    drugs: list[str]
    condition: str
    seen_ncts: set[str]
    drug_profiles: list[dict[str, Any]] = field(default_factory=list)
    pair_flags: list[dict[str, Any]] = field(default_factory=list)
    trials: list[dict[str, Any]] = field(default_factory=list)
    risk_score: float = 0.0
    triage_level: str = "LOW MONITORING"
    messages: list[PharmaBusMessage] = field(default_factory=list)

    def emit(self, sender: str, recipient: str, phase: str, content: str, confidence: float = 0.93) -> None:
        self.messages.append(PharmaBusMessage(sender, recipient, phase, content, round(confidence, 2)))


class OpenFDASafetyScoutAgent:
    """Sub-Agent 1: Queries OpenFDA FAERS adverse events, FDA labels, and PubChem chemistry in parallel."""

    name = "OpenFDASafetyScoutAgent"

    def run(self, ctx: PharmaContext) -> None:
        def _profile_drug(d: str) -> dict[str, Any]:
            faers = fetch_openfda_adverse_events(d)
            label = fetch_openfda_label_interactions(d)
            chem = fetch_pubchem_properties(d)
            return {**faers, **label, **chem}

        with ThreadPoolExecutor(max_workers=6) as pool:
            ctx.drug_profiles = list(pool.map(_profile_drug, ctx.drugs))

        boxed_cnt = sum(1 for p in ctx.drug_profiles if p["has_boxed_warning"])
        ctx.emit(
            self.name,
            "InteractionGraphAgent",
            "SENSE-FDA",
            f"Profiled {len(ctx.drug_profiles)} drugs across OpenFDA FAERS/Labels & PubChem ({boxed_cnt} boxed warnings).",
            confidence=0.95,
        )


class InteractionGraphAgent:
    """Sub-Agent 2: Cross-checks drug pairs against FDA label text and pharmacological rules."""

    name = "InteractionGraphAgent"

    def run(self, ctx: PharmaContext) -> None:
        lower_drugs = [d.strip().lower() for d in ctx.drugs]
        flags: list[dict[str, Any]] = []
        for i in range(len(lower_drugs)):
            for j in range(i + 1, len(lower_drugs)):
                a, b = lower_drugs[i], lower_drugs[j]
                pair = tuple(sorted((a, b)))
                if pair in KNOWN_PAIR_SYNERGIES:
                    desc, weight = KNOWN_PAIR_SYNERGIES[pair]
                    flags.append({"pair": f"{a.title()} + {b.title()}", "mechanism": desc, "severity_pts": weight, "evidence": "Pharmacological + FDA Rule"})
                else:
                    # Check live FDA interaction paragraph cross-mentions
                    p_a = ctx.drug_profiles[i]["interaction_text"].lower() if i < len(ctx.drug_profiles) else ""
                    p_b = ctx.drug_profiles[j]["interaction_text"].lower() if j < len(ctx.drug_profiles) else ""
                    if b in p_a or a in p_b:
                        flags.append({"pair": f"{a.title()} + {b.title()}", "mechanism": "Explicit cross-mention in live FDA Drug Interactions label.", "severity_pts": 24, "evidence": "Live OpenFDA Label"})

        ctx.pair_flags = flags
        ctx.emit(
            self.name,
            "ClinicalTrialEvidenceAgent",
            "CROSS-CHECK",
            f"Evaluated {len(lower_drugs)*(len(lower_drugs)-1)//2} drug pairs; flagged {len(flags)} interaction signal(s).",
            confidence=0.91,
        )


class ClinicalTrialEvidenceAgent:
    """Sub-Agent 3: Pulls live ClinicalTrials.gov v2 studies for ongoing safety/efficacy context."""

    name = "ClinicalTrialEvidenceAgent"

    def run(self, ctx: PharmaContext) -> None:
        query = f"{' '.join(ctx.drugs[:2])} {ctx.condition}".strip()
        res = fetch_clinical_trials(query, limit=5)
        ctx.trials = res["studies"]
        unseen = sum(1 for t in ctx.trials if t["nct_id"] not in ctx.seen_ncts)
        ctx.emit(
            self.name,
            "PolypharmacyRiskTriageAgent",
            "EVIDENCE",
            f"Retrieved {len(ctx.trials)} ClinicalTrials.gov v2 studies ({unseen} unseen vs memory).",
            confidence=0.94,
        )


class PolypharmacyRiskTriageAgent:
    """Sub-Agent 4: Computes composite polypharmacy risk score & clinical pharmacist review gate."""

    name = "PolypharmacyRiskTriageAgent"

    def run(self, ctx: PharmaContext) -> None:
        boxed_pts = sum(14 for p in ctx.drug_profiles if p["has_boxed_warning"])
        pair_pts = sum(f["severity_pts"] for f in ctx.pair_flags)
        poly_load = max(0, (len(ctx.drugs) - 1) * 6)
        score = round(min(99.0, 10.0 + boxed_pts + pair_pts + poly_load), 1)
        ctx.risk_score = score

        if score >= 65:
            ctx.triage_level = "HIGH PRIORITY PHARMACIST REVIEW"
        elif score >= 35:
            ctx.triage_level = "MODERATE MONITORING"
        else:
            ctx.triage_level = "ROUTINE MONITORING"

        ctx.emit(
            self.name,
            "MedMesh Director",
            "TRIAGE",
            f"Computed Polypharmacy Risk={score}/100 ({ctx.triage_level}). Educational decision-support only.",
            confidence=0.95,
        )
