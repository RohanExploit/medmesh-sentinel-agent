"""Model-based persistent memory for MedMesh Sentinel pharmacovigilance watchlists."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STATE: dict[str, Any] = {
    "agent_name": "MedMesh Clinical Safety Director",
    "seen_trial_ncts": [],
    "triage_history": [],
    "total_screenings": 0,
    "last_screening_utc": None,
}


class PharmaMemoryStore:
    """Stores deduplicated ClinicalTrials NCT IDs and historical polypharmacy triage runs."""

    def __init__(self, state_path: Path | str | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.path = Path(state_path) if state_path else base_dir / "state" / "pharma_memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return json.loads(json.dumps(DEFAULT_STATE))
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for key, val in DEFAULT_STATE.items():
                data.setdefault(key, json.loads(json.dumps(val)))
            return data
        except Exception:
            return json.loads(json.dumps(DEFAULT_STATE))

    def save(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def update_after_screening(
        self,
        regimen: list[str],
        nct_ids: list[str],
        risk_score: float,
        triage_level: str,
        summary: str,
    ) -> dict[str, Any]:
        state = self.load()
        seen = set(state.get("seen_trial_ncts", []))
        new_ncts = [nid for nid in nct_ids if nid not in seen]
        state["seen_trial_ncts"] = (state.get("seen_trial_ncts", []) + new_ncts)[-250:]

        now_iso = datetime.now(timezone.utc).isoformat()
        state["total_screenings"] = int(state.get("total_screenings", 0)) + 1
        state["last_screening_utc"] = now_iso
        state["triage_history"].append(
            {
                "timestamp_utc": now_iso,
                "regimen": ", ".join(regimen),
                "triage_level": triage_level,
                "risk_score": round(risk_score, 1),
                "new_trials_seen": len(new_ncts),
                "summary": summary[:200],
            }
        )
        state["triage_history"] = state["triage_history"][-30:]
        self.save(state)
        return state
