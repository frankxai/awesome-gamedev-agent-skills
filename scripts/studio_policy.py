#!/usr/bin/env python3
"""Small fail-closed reference policy core for governed game-studio adapters.

This module is intentionally engine-neutral and standard-library only. It does not
start MCP servers; it demonstrates the admission, receipt, transition, and budget
invariants an executor must preserve.
"""
from __future__ import annotations

import hashlib
import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

SHA256 = "sha256:"
ALLOWED_TRANSITIONS = {
    "DISCOVER": {"BRIEF"}, "BRIEF": {"ARCHITECT"},
    "ARCHITECT": {"ASSET_MANIFEST"}, "ASSET_MANIFEST": {"PROTOTYPE"},
    "PROTOTYPE": {"PLAYTEST", "HOLD"}, "PLAYTEST": {"HARDEN", "HOLD"},
    "HARDEN": {"RELEASE_CANDIDATE", "HOLD"},
    "RELEASE_CANDIDATE": {"HUMAN_APPROVAL", "HOLD"},
    "HUMAN_APPROVAL": {"RELEASE", "HOLD"}, "RELEASE": {"LIVEOPS", "HOLD"},
    "HOLD": {"PROTOTYPE", "PLAYTEST", "HARDEN", "RELEASE_CANDIDATE"},
}

class PolicyViolation(ValueError):
    """Fail-closed policy rejection."""


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return SHA256 + hashlib.sha256(payload).hexdigest()


def _require_sha256(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.startswith(SHA256) or len(value) != 71:
        raise PolicyViolation(f"{field} must be sha256:<64 hex chars>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise PolicyViolation(f"{field} must be hexadecimal") from exc


def _contained(root: str, target: str) -> bool:
    root_path = Path(root).resolve()
    target_path = Path(target).resolve()
    try:
        target_path.relative_to(root_path)
        return True
    except ValueError:
        return False


def admit_tool_call(policy: dict[str, Any], call: dict[str, Any], now_epoch: int) -> dict[str, Any]:
    """Admit one bounded call or raise PolicyViolation before execution."""
    required = {"server_id", "server_version", "tool", "project_root", "target_path", "egress_host", "actor", "run_id"}
    missing = required - set(call)
    if missing:
        raise PolicyViolation(f"call missing {sorted(missing)}")
    if call["server_id"] != policy.get("server_id"):
        raise PolicyViolation("unregistered server")
    if call["server_version"] != policy.get("server_version"):
        raise PolicyViolation("stale or unapproved server version")
    if call["tool"] not in policy.get("allowed_tools", []):
        raise PolicyViolation("unapproved tool")
    if call["project_root"] != policy.get("project_root"):
        raise PolicyViolation("unapproved project root")
    if not _contained(call["project_root"], call["target_path"]):
        raise PolicyViolation("target escapes project root")
    host = call.get("egress_host")
    if host and host not in policy.get("allowed_egress_hosts", []):
        raise PolicyViolation("unapproved egress host")
    if policy.get("auth_required") and int(call.get("auth_expires_at", 0)) <= now_epoch:
        raise PolicyViolation("authorization absent or expired")
    admitted = deepcopy(call)
    admitted["policy_version"] = policy.get("policy_version")
    admitted["admission"] = "ALLOW"
    admitted["request_hash"] = canonical_hash(call)
    return admitted


def validate_3d_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Reject a generated 3D asset until it is demonstrably engine-ready."""
    required = {
        "asset_id", "source_url", "license", "scale_meters", "up_axis", "poly_count",
        "poly_cap", "uv_sets", "pbr_maps", "lods", "collision", "engine_import_hash",
        "runtime_memory_mb", "memory_cap_mb", "frame_time_ms", "frame_time_cap_ms",
    }
    missing = required - set(asset)
    if missing:
        raise PolicyViolation(f"3d asset missing {sorted(missing)}")
    if asset["license"] in {"unknown", "NOASSERTION", ""}:
        raise PolicyViolation("3d asset license is not cleared")
    if not isinstance(asset["scale_meters"], (int, float)) or asset["scale_meters"] <= 0:
        raise PolicyViolation("3d asset scale must be positive")
    if asset["up_axis"] not in {"Y", "Z"}:
        raise PolicyViolation("3d asset up axis must be Y or Z")
    if asset["poly_count"] > asset["poly_cap"]:
        raise PolicyViolation("3d asset exceeds polygon budget")
    if int(asset["uv_sets"]) < 1:
        raise PolicyViolation("3d asset requires UVs")
    if not {"base_color", "normal", "roughness", "metallic"}.issubset(set(asset["pbr_maps"])):
        raise PolicyViolation("3d asset requires the baseline PBR map set")
    if not isinstance(asset["lods"], list) or not asset["lods"]:
        raise PolicyViolation("3d asset requires at least one LOD")
    if asset["collision"] is not True:
        raise PolicyViolation("3d asset requires a collision or navigation proxy")
    _require_sha256(asset["engine_import_hash"], "engine_import_hash")
    if asset["runtime_memory_mb"] > asset["memory_cap_mb"]:
        raise PolicyViolation("3d asset exceeds runtime memory budget")
    if asset["frame_time_ms"] > asset["frame_time_cap_ms"]:
        raise PolicyViolation("3d asset exceeds frame-time budget")
    result = deepcopy(asset)
    result["decision"] = "READY"
    result["manifest_hash"] = canonical_hash(asset)
    return result


class BudgetLedger:
    """Concurrency-safe hard ceilings. Exhaustion always returns HOLD."""
    def __init__(self, ceilings: dict[str, float]) -> None:
        self.ceilings = dict(ceilings)
        self.used = {key: 0.0 for key in ceilings}
        self._lock = threading.Lock()

    def reserve(self, request: dict[str, float]) -> dict[str, Any]:
        with self._lock:
            unknown = set(request) - set(self.ceilings)
            if unknown:
                raise PolicyViolation(f"unknown budget dimensions {sorted(unknown)}")
            if any(value < 0 for value in request.values()):
                raise PolicyViolation("budget request cannot be negative")
            if any(self.used[key] + value > self.ceilings[key] for key, value in request.items()):
                return {"decision": "HOLD", "used": dict(self.used), "ceilings": dict(self.ceilings)}
            for key, value in request.items():
                self.used[key] += value
            return {"decision": "ALLOW", "used": dict(self.used), "ceilings": dict(self.ceilings)}


class WorkflowGate:
    """Reject stale/self-approved/duplicate transitions before state changes."""
    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._lock = threading.Lock()

    def advance(self, receipt: dict[str, Any]) -> dict[str, Any]:
        required = {"from_state", "to_state", "actor", "verifier", "artifact_hash", "evidence_hashes", "idempotency_key", "policy_version"}
        missing = required - set(receipt)
        if missing:
            raise PolicyViolation(f"transition missing {sorted(missing)}")
        if receipt["to_state"] not in ALLOWED_TRANSITIONS.get(receipt["from_state"], set()):
            raise PolicyViolation("invalid state transition")
        if receipt["actor"] == receipt["verifier"]:
            raise PolicyViolation("maker cannot verify its own transition")
        _require_sha256(receipt["artifact_hash"], "artifact_hash")
        evidence = receipt["evidence_hashes"]
        if not isinstance(evidence, list) or not evidence:
            raise PolicyViolation("at least one evidence hash is required")
        for value in evidence:
            _require_sha256(value, "evidence_hash")
        if receipt["to_state"] == "RELEASE" and receipt.get("human_approved") is not True:
            raise PolicyViolation("release requires explicit human approval")
        key = receipt["idempotency_key"]
        with self._lock:
            if key in self._seen:
                raise PolicyViolation("duplicate idempotency key")
            self._seen.add(key)
        result = deepcopy(receipt)
        result["decision"] = "ALLOW"
        result["receipt_hash"] = canonical_hash(receipt)
        return result
