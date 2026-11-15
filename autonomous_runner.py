"""Headless autonomous runner for scheduled MedMesh pharmacovigilance watchlist sweeps."""

from __future__ import annotations

import json
import os

from agents.orchestrator import MedMeshDirector


def main() -> None:
    drugs_raw = os.environ.get("MEDMESH_WATCHLIST", "Warfarin,Aspirin,Atorvastatin")
    drugs = [d.strip() for d in drugs_raw.split(",") if d.strip()]
    res = MedMeshDirector().run_screening(drugs=drugs, condition="cardiovascular")
    print(
        json.dumps(
            {
                "regimen": res["drugs"],
                "triage_level": res["triage_level"],
                "risk_score": res["risk_score"],
                "pair_flags": len(res["pair_flags"]),
                "provider": res["synthesis"]["provider"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
