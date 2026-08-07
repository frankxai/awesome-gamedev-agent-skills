#!/usr/bin/env python3
"""Fail-closed, engine-neutral *reference* policy primitives.

This standard-library module does not start MCP servers and is not an OS sandbox,
persistent ledger, or production authorization service. It demonstrates invariants
that a trusted executor must preserve and denies trust-sensitive actions when the
required verifier adapter is absent.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

SHA256 = "sha256:"
POLICY_FIELDS = {
    "policy_version", "server_id", "server_version", "distribution_sha256", "transport",
    "auth_required", "project_root", "allowed_tools", "allowed_egress_hosts", "action_tier", "revoked",
}
ASSET_FIELDS = {
    "asset_id", "source_url", "license", "scale_meters", "up_axis", "poly_count", "poly_cap",
    "uv_sets", "pbr_maps", "lods", "collision", "engine_import_hash", "runtime_memory_mb",
    "memory_cap_mb", "frame_time_ms", "frame_time_cap_ms",
}
TRANSITION_FIELDS = {
    "run_id", "from_state", "to_state", "actor", "verifier", "artifact_hash", "evidence_hashes",
    "idempotency_key", "policy_version", "timestamp", "recovery", "approval_receipt",
}
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


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def canonical_hash(value: Any) -> str:
    return SHA256 + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_sha256(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.startswith(SHA256) or len(value) != 71:
        raise PolicyViolation(f"{field} must be sha256:<64 hex chars>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise PolicyViolation(f"{field} must be hexadecimal") from exc


def _require_exact_fields(value: dict[str, Any], allowed: set[str], required: set[str], label: str) -> None:
    missing = required - set(value)
    extra = set(value) - allowed
    if missing:
        raise PolicyViolation(f"{label} missing {sorted(missing)}")
    if extra:
        raise PolicyViolation(f"{label} has unexpected fields {sorted(extra)}")


def _contained(root: str, target: str) -> bool:
    root_path = Path(root).resolve()
    target_path = Path(target).resolve()
    try:
        target_path.relative_to(root_path)
        return True
    except ValueError:
        return False


AuthorizationVerifier = Callable[[dict[str, Any], dict[str, Any], int], bool]


def _nonempty_string(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise PolicyViolation(f"{field} must be a non-empty string")


def _integer(value: Any, field: str, minimum: int = 0) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PolicyViolation(f"{field} must be an integer >= {minimum}")


def _number(value: Any, field: str, minimum: float = 0.0) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
        raise PolicyViolation(f"{field} must be a number >= {minimum}")


def _unique_string_list(value: Any, field: str, nonempty: bool = False) -> None:
    if not isinstance(value, list) or (nonempty and not value) or not all(isinstance(item, str) for item in value) or len(value) != len(set(value)):
        raise PolicyViolation(f"{field} must be a {'non-empty ' if nonempty else ''}unique string list")


def _validate_policy(policy: dict[str, Any]) -> None:
    _require_exact_fields(policy, POLICY_FIELDS, POLICY_FIELDS - {"revoked"}, "policy")
    for field in ("policy_version", "server_id", "server_version", "project_root"):
        _nonempty_string(policy[field], field)
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in policy["server_id"]):
        raise PolicyViolation("server_id must match ^[a-z0-9-]+$")
    _require_sha256(policy["distribution_sha256"], "distribution_sha256")
    if policy["transport"] not in {"stdio", "http", "sse"}:
        raise PolicyViolation("transport is invalid")
    if not isinstance(policy["auth_required"], bool) or not isinstance(policy.get("revoked", False), bool):
        raise PolicyViolation("auth_required and revoked must be booleans")
    _unique_string_list(policy["allowed_tools"], "allowed_tools", nonempty=True)
    _unique_string_list(policy["allowed_egress_hosts"], "allowed_egress_hosts")
    if policy["action_tier"] not in {"read", "write", "execute", "deploy"}:
        raise PolicyViolation("action_tier is invalid")


def _admit_tool_call(
    policy: dict[str, Any], call: dict[str, Any], now_epoch: int,
    authorization_verifier: AuthorizationVerifier | None,
) -> dict[str, Any]:
    """Internal operation path. Trust adapters are fixed at executor bootstrap."""
    _validate_policy(policy)
    if policy.get("revoked", False):
        raise PolicyViolation("policy is revoked")
    _require_sha256(policy["distribution_sha256"], "distribution_sha256")
    required_call = {
        "server_id", "server_version", "distribution_sha256", "transport", "action_tier", "tool",
        "project_root", "target_path", "egress_host", "actor", "run_id", "auth_expires_at", "authorization_id",
    }
    _require_exact_fields(call, required_call, required_call, "call")
    for field in ("server_id", "server_version", "distribution_sha256", "transport", "action_tier", "tool", "project_root", "target_path", "actor", "run_id", "authorization_id"):
        _nonempty_string(call[field], field)
    if call["egress_host"] is not None and not isinstance(call["egress_host"], str):
        raise PolicyViolation("egress_host must be a string or null")
    _integer(call["auth_expires_at"], "auth_expires_at")
    _require_sha256(call["distribution_sha256"], "distribution_sha256")
    for field in ("server_id", "server_version", "distribution_sha256", "transport", "action_tier", "project_root"):
        if call[field] != policy[field]:
            raise PolicyViolation(f"unapproved {field}")
    if call["tool"] not in policy["allowed_tools"]:
        raise PolicyViolation("unapproved tool")
    if not _contained(call["project_root"], call["target_path"]):
        raise PolicyViolation("target escapes project root")
    host = call["egress_host"]
    if host and host not in policy["allowed_egress_hosts"]:
        raise PolicyViolation("unapproved egress host")
    if policy["auth_required"]:
        if int(call["auth_expires_at"]) <= now_epoch:
            raise PolicyViolation("authorization expired")
        if authorization_verifier is None or not authorization_verifier(call, policy, now_epoch):
            raise PolicyViolation("authorization is not verified by a trusted adapter")
    admitted = deepcopy(call)
    admitted.update(policy_version=policy["policy_version"], admission="ALLOW", request_hash=canonical_hash(call))
    return admitted


class AdmissionExecutor:
    """Trusted-bootstrap boundary; operation callers submit calls but cannot replace trust adapters."""
    def __init__(self, policy: dict[str, Any], authorization_verifier: AuthorizationVerifier | None) -> None:
        _validate_policy(policy)
        self._policy = deepcopy(policy)
        self._authorization_verifier = authorization_verifier

    def admit(self, call: dict[str, Any], now_epoch: int) -> dict[str, Any]:
        return _admit_tool_call(self._policy, call, now_epoch, self._authorization_verifier)


def validate_3d_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Reject a generated 3D asset until it is demonstrably engine-ready."""
    _require_exact_fields(asset, ASSET_FIELDS, ASSET_FIELDS, "3d asset")
    for field in ("asset_id", "source_url", "license", "up_axis", "engine_import_hash"):
        _nonempty_string(asset[field], field)
    if not asset["source_url"].startswith("https://"):
        raise PolicyViolation("source_url must be https")
    _number(asset["scale_meters"], "scale_meters")
    if asset["scale_meters"] <= 0:
        raise PolicyViolation("3d asset scale must be positive")
    _integer(asset["poly_count"], "poly_count")
    _integer(asset["poly_cap"], "poly_cap", minimum=1)
    _integer(asset["uv_sets"], "uv_sets", minimum=1)
    _unique_string_list(asset["pbr_maps"], "pbr_maps", nonempty=True)
    if not set(asset["pbr_maps"]).issubset({"base_color", "normal", "roughness", "metallic", "ao", "emissive"}):
        raise PolicyViolation("pbr_maps contains an unsupported map")
    if not isinstance(asset["lods"], list) or not asset["lods"]:
        raise PolicyViolation("lods must be a non-empty integer list")
    for lod in asset["lods"]:
        _integer(lod, "lod", minimum=0)
    if not isinstance(asset["collision"], bool):
        raise PolicyViolation("collision must be a boolean")
    for field in ("runtime_memory_mb", "memory_cap_mb", "frame_time_ms", "frame_time_cap_ms"):
        _number(asset[field], field)
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
    result.update(decision="READY", manifest_hash=canonical_hash(asset))
    return result


class BudgetLedger:
    """Process-local reference counter; production requires a persistent per-run ledger."""
    def __init__(self, run_id: str, budget_class: str, ceilings: dict[str, float]) -> None:
        if not run_id or not budget_class:
            raise PolicyViolation("budget ledger requires run_id and budget_class")
        self.run_id, self.budget_class = run_id, budget_class
        self.ceilings = dict(ceilings)
        self.used = {key: 0.0 for key in ceilings}
        self._lock = threading.Lock()

    def reserve(self, run_id: str, request: dict[str, float]) -> dict[str, Any]:
        if run_id != self.run_id:
            raise PolicyViolation("budget request is bound to a different run")
        with self._lock:
            unknown = set(request) - set(self.ceilings)
            if unknown:
                raise PolicyViolation(f"unknown budget dimensions {sorted(unknown)}")
            if any(value < 0 for value in request.values()):
                raise PolicyViolation("budget request cannot be negative")
            if any(self.used[key] + value > self.ceilings[key] for key, value in request.items()):
                return {"decision": "HOLD", "run_id": self.run_id, "budget_class": self.budget_class, "used": dict(self.used), "ceilings": dict(self.ceilings)}
            for key, value in request.items():
                self.used[key] += value
            return {"decision": "ALLOW", "run_id": self.run_id, "budget_class": self.budget_class, "used": dict(self.used), "ceilings": dict(self.ceilings)}


class ApprovalVerifier:
    """Trusted-bootstrap verifier for artifact/run-bound approval receipts.

    Production signing keys and verifier construction must live outside the agent/request
    process. This class intentionally exposes no signing method.
    """
    FIELDS = {"approver_id", "run_id", "artifact_hash", "actor", "issued_at", "expires_at", "nonce", "signature"}

    def __init__(self, approver_secrets: dict[str, bytes], revoked_approvers: set[str] | None = None) -> None:
        if not approver_secrets or not all(isinstance(key, str) and key and isinstance(secret, bytes) and secret for key, secret in approver_secrets.items()):
            raise PolicyViolation("trusted bootstrap requires non-empty approver IDs and byte secrets")
        self._secrets = dict(approver_secrets)
        self._revoked = set(revoked_approvers or set())

    def verify(self, approval: dict[str, Any], transition: dict[str, Any], now_epoch: int) -> None:
        _require_exact_fields(approval, self.FIELDS, self.FIELDS, "approval")
        for field in ("approver_id", "run_id", "actor", "nonce", "signature"):
            _nonempty_string(approval[field], field)
        _require_sha256(approval["artifact_hash"], "artifact_hash")
        _integer(approval["issued_at"], "issued_at")
        _integer(approval["expires_at"], "expires_at", minimum=1)
        if len(approval["signature"]) != 64:
            raise PolicyViolation("approval signature must be 64 hex characters")
        try:
            int(approval["signature"], 16)
        except ValueError as exc:
            raise PolicyViolation("approval signature must be hexadecimal") from exc
        approver = approval["approver_id"]
        if approver not in self._secrets or approver in self._revoked:
            raise PolicyViolation("approver is unknown or revoked")
        if not int(approval["issued_at"]) <= now_epoch < int(approval["expires_at"]):
            raise PolicyViolation("approval is not current")
        for field in ("run_id", "artifact_hash", "actor"):
            if approval[field] != transition[field]:
                raise PolicyViolation(f"approval is not bound to transition {field}")
        unsigned = {key: approval[key] for key in self.FIELDS - {"signature"}}
        expected = hmac.new(self._secrets[approver], _canonical_bytes(unsigned), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, approval["signature"]):
            raise PolicyViolation("approval signature is invalid")


class WorkflowGate:
    """Process-local transition checker; production must persist state and idempotency."""
    def __init__(self, trusted_verifiers: set[str], approval_verifier: ApprovalVerifier | None = None) -> None:
        if not trusted_verifiers or not all(isinstance(value, str) and value for value in trusted_verifiers):
            raise PolicyViolation("at least one non-empty trusted verifier is required")
        self._trusted_verifiers = set(trusted_verifiers)
        self._approval_verifier = approval_verifier
        self._seen: set[str] = set()
        self._lock = threading.Lock()

    def advance(self, receipt: dict[str, Any], now_epoch: int) -> dict[str, Any]:
        required = TRANSITION_FIELDS - {"approval_receipt"}
        _require_exact_fields(receipt, TRANSITION_FIELDS, required, "transition")
        for field in ("run_id", "from_state", "to_state", "actor", "verifier", "artifact_hash", "idempotency_key", "policy_version", "recovery"):
            _nonempty_string(receipt[field], field)
        if len(receipt["idempotency_key"]) < 8:
            raise PolicyViolation("idempotency_key must contain at least 8 characters")
        _integer(receipt["timestamp"], "timestamp")
        if "approval_receipt" in receipt and not isinstance(receipt["approval_receipt"], dict):
            raise PolicyViolation("approval_receipt must be an object")
        if receipt["to_state"] not in ALLOWED_TRANSITIONS.get(receipt["from_state"], set()):
            raise PolicyViolation("invalid state transition")
        if receipt["actor"] == receipt["verifier"] or receipt["verifier"] not in self._trusted_verifiers:
            raise PolicyViolation("transition requires an independent trusted verifier")
        if not isinstance(receipt["timestamp"], int) or receipt["timestamp"] > now_epoch:
            raise PolicyViolation("transition timestamp is invalid")
        if receipt["recovery"] not in {"none", "retry", "rollback", "compensate"}:
            raise PolicyViolation("invalid recovery mode")
        _require_sha256(receipt["artifact_hash"], "artifact_hash")
        evidence = receipt["evidence_hashes"]
        if not isinstance(evidence, list) or not evidence:
            raise PolicyViolation("at least one evidence hash is required")
        for value in evidence:
            _require_sha256(value, "evidence_hash")
        if receipt["to_state"] == "RELEASE":
            if self._approval_verifier is None or "approval_receipt" not in receipt:
                raise PolicyViolation("release requires a trusted approval verifier and signed receipt")
            self._approval_verifier.verify(receipt["approval_receipt"], receipt, now_epoch)
        elif "approval_receipt" in receipt:
            raise PolicyViolation("approval receipt is only valid for RELEASE")
        key = receipt["idempotency_key"]
        with self._lock:
            if key in self._seen:
                raise PolicyViolation("duplicate idempotency key")
            self._seen.add(key)
        result = deepcopy(receipt)
        result.update(decision="ALLOW", receipt_hash=canonical_hash(receipt))
        return result
