"""Keyless live medical sensors: OpenFDA FAERS/Label, ClinicalTrials.gov v2, PubChem."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

HEADERS = {"User-Agent": "MedMesh-Sentinel-Agent/1.0"}


def fetch_openfda_adverse_events(drug_name: str, timeout: float = 5.0) -> dict[str, Any]:
    """Query OpenFDA FAERS API for adverse event volume and top reactions."""
    clean = drug_name.strip().lower()
    try:
        resp = requests.get(
            "https://api.fda.gov/drug/event.json",
            params={"search": f'patient.drug.medicinalproduct:"{clean}"', "count": "patient.reaction.reactionmeddrapt.exact", "limit": 5},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        top_reactions = [f"{r.get('term', '')} ({r.get('count', 0)})" for r in results[:4]]
        total_top = sum(int(r.get("count") or 0) for r in results)
        return {
            "drug": clean.title(),
            "top_reactions": top_reactions,
            "top_reaction_volume": total_top,
            "source": "live-openfda-faers",
        }
    except Exception as exc:
        return {
            "drug": clean.title(),
            "top_reactions": ["Nausea (fallback)", "Fatigue (fallback)"],
            "top_reaction_volume": 0,
            "source": f"openfda-backup ({type(exc).__name__})",
        }


def fetch_openfda_label_interactions(drug_name: str, timeout: float = 5.0) -> dict[str, Any]:
    """Fetch official FDA drug label interaction and boxed warning snippets."""
    clean = drug_name.strip().lower()
    try:
        resp = requests.get(
            "https://api.fda.gov/drug/label.json",
            params={"search": f'openfda.generic_name:"{clean}" OR openfda.brand_name:"{clean}"', "limit": 1},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        item = (resp.json().get("results") or [{}])[0]
        interactions = " ".join(item.get("drug_interactions", []))[:600]
        boxed = " ".join(item.get("boxed_warning", []))[:300]
        return {
            "drug": clean.title(),
            "interaction_text": interactions or "No explicit interaction paragraph in matched label.",
            "has_boxed_warning": bool(boxed),
            "boxed_excerpt": boxed,
            "source": "live-openfda-label",
        }
    except Exception as exc:
        return {
            "drug": clean.title(),
            "interaction_text": "Label lookup temporarily unavailable.",
            "has_boxed_warning": False,
            "boxed_excerpt": "",
            "source": f"label-backup ({type(exc).__name__})",
        }


def fetch_pubchem_properties(drug_name: str, timeout: float = 4.5) -> dict[str, Any]:
    """Fetch molecular formula and molecular weight from NCBI PubChem PUG REST."""
    clean = quote(drug_name.strip().lower())
    try:
        resp = requests.get(
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{clean}/property/MolecularFormula,MolecularWeight/JSON",
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        props = (resp.json().get("PropertyTable", {}).get("Properties") or [{}])[0]
        return {
            "formula": props.get("MolecularFormula", "N/A"),
            "molecular_weight": props.get("MolecularWeight", "N/A"),
            "source": "live-pubchem",
        }
    except Exception:
        return {"formula": "N/A", "molecular_weight": "N/A", "source": "pubchem-backup"}


def fetch_clinical_trials(query: str, limit: int = 5, timeout: float = 5.5) -> dict[str, Any]:
    """Query ClinicalTrials.gov API v2 for active/recruiting trials."""
    clean = query.strip() or "warfarin aspirin"
    try:
        resp = requests.get(
            "https://clinicaltrials.gov/api/v2/studies",
            params={"query.term": clean, "pageSize": limit, "format": "json"},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        studies = []
        for s in resp.json().get("studies", []):
            ps = s.get("protocolSection", {})
            ident = ps.get("identificationModule", {})
            status = ps.get("statusModule", {})
            design = ps.get("designModule", {})
            studies.append(
                {
                    "nct_id": ident.get("nctId", "NCT-UNKNOWN"),
                    "title": (ident.get("briefTitle") or "Untitled Study")[:105],
                    "status": status.get("overallStatus", "UNKNOWN"),
                    "phases": ", ".join(design.get("phases", [])) or "N/A",
                }
            )
        return {"studies": studies, "source": "live-clinicaltrials-v2"}
    except Exception as exc:
        return {"studies": [], "source": f"ctgov-backup ({type(exc).__name__})"}
