"""Analyst approval records for a commentary draft.

The model never writes an approval on its own. A person passes a reviewer name.
The record is bound to the exact draft bytes, so an edit after the decision
makes the decision stale.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

Decision = Literal["approved", "rejected"]
APPROVAL_SUFFIX = ".approval.json"


def approval_path(draft: Path) -> Path:
    return Path(str(draft) + APPROVAL_SUFFIX)


def draft_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def require_draft(text: str) -> None:
    if "SYNTHETIC DATA" not in text or "Status: DRAFT" not in text:
        raise ValueError("That file is not a commentary draft from fpa-model.")


def decide(
    draft: Path,
    *,
    reviewer: str,
    note: str,
    status: Decision,
    now: datetime | None = None,
) -> Path:
    reviewer_name = reviewer.strip()
    if not reviewer_name:
        raise ValueError("A reviewer name is required.")
    if status not in ("approved", "rejected"):
        raise ValueError(f"unsupported decision: {status}")
    text = draft.read_text(encoding="utf-8")
    require_draft(text)
    moment = now if now is not None else datetime.now(UTC)
    payload = {
        "status": status,
        "reviewer": reviewer_name,
        "note": note.strip(),
        "draft_sha256": draft_sha256(text),
        "decided_at": moment.isoformat(),
        "synthetic": True,
    }
    destination = approval_path(draft)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return destination


def review_status(draft: Path) -> str:
    """Return pending, approved, rejected, or stale."""
    sidecar = approval_path(draft)
    if not sidecar.is_file():
        return "pending"
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    current = draft_sha256(draft.read_text(encoding="utf-8"))
    if payload.get("draft_sha256") != current:
        return "stale"
    status = payload.get("status")
    if status in ("approved", "rejected"):
        return str(status)
    return "stale"
