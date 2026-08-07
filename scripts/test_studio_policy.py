#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from studio_policy import (
    ApprovalAuthority, BudgetLedger, PolicyViolation, WorkflowGate,
    admit_tool_call, canonical_hash, validate_3d_asset,
)

HASH = "sha256:" + "a" * 64
DIST = "sha256:" + "b" * 64
NOW = 100

class StudioPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = str(Path(self.tmp.name).resolve())
        self.policy = {
            "policy_version": "1.0.0", "server_id": "engine-test", "server_version": "1.2.3",
            "distribution_sha256": DIST, "transport": "stdio", "auth_required": True,
            "project_root": self.root, "allowed_tools": ["compile", "capture"],
            "allowed_egress_hosts": ["localhost"], "action_tier": "execute", "revoked": False,
        }
        self.call = {
            "server_id": "engine-test", "server_version": "1.2.3", "distribution_sha256": DIST,
            "transport": "stdio", "action_tier": "execute", "tool": "compile",
            "project_root": self.root, "target_path": str(Path(self.root) / "game"),
            "egress_host": "localhost", "auth_expires_at": 200, "authorization_id": "auth-1",
            "actor": "maker", "run_id": "run-1",
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def trusted_auth(call, policy, now):
        return call["authorization_id"] == "auth-1" and call["actor"] == "maker"

    def test_allowed_call_emits_hash_bound_receipt(self) -> None:
        result = admit_tool_call(self.policy, self.call, NOW, self.trusted_auth)
        self.assertEqual(result["admission"], "ALLOW")
        self.assertTrue(result["request_hash"].startswith("sha256:"))

    def test_admission_fails_for_revocation_distribution_and_absent_trusted_auth(self) -> None:
        revoked = dict(self.policy, revoked=True)
        with self.assertRaises(PolicyViolation): admit_tool_call(revoked, self.call, NOW, self.trusted_auth)
        wrong_dist = dict(self.call, distribution_sha256=HASH)
        with self.assertRaises(PolicyViolation): admit_tool_call(self.policy, wrong_dist, NOW, self.trusted_auth)
        with self.assertRaises(PolicyViolation): admit_tool_call(self.policy, self.call, NOW)

    def test_unknown_tool_version_egress_auth_and_path_fail_closed(self) -> None:
        cases = [
            ("tool", "delete-project"), ("server_version", "0.0.1"),
            ("egress_host", "example.com"), ("auth_expires_at", 99),
            ("target_path", str(Path(self.root).parent / "escape")),
        ]
        for field, value in cases:
            call = dict(self.call); call[field] = value
            with self.subTest(field=field), self.assertRaises(PolicyViolation):
                admit_tool_call(self.policy, call, NOW, self.trusted_auth)

    def transition(self, **updates):
        value = {
            "run_id": "run-1", "from_state": "PROTOTYPE", "to_state": "PLAYTEST",
            "actor": "maker", "verifier": "checker", "artifact_hash": HASH,
            "evidence_hashes": [HASH], "idempotency_key": "transition-1",
            "policy_version": "1.0.0", "timestamp": NOW, "recovery": "none",
        }
        value.update(updates)
        return value

    def test_workflow_rejects_untrusted_self_verifier_duplicate_and_schema_drift(self) -> None:
        gate = WorkflowGate({"checker"})
        base = self.transition()
        self.assertEqual(gate.advance(base, NOW)["decision"], "ALLOW")
        with self.assertRaises(PolicyViolation): gate.advance(base, NOW)
        with self.assertRaises(PolicyViolation): WorkflowGate({"checker"}).advance(self.transition(verifier="maker"), NOW)
        with self.assertRaises(PolicyViolation): WorkflowGate({"checker"}).advance(self.transition(verifier="stranger"), NOW)
        missing_timestamp = self.transition(); del missing_timestamp["timestamp"]
        with self.assertRaises(PolicyViolation): WorkflowGate({"checker"}).advance(missing_timestamp, NOW)
        with self.assertRaises(PolicyViolation): WorkflowGate({"checker"}).advance(self.transition(unexpected=True), NOW)

    def test_release_requires_current_signed_artifact_bound_approval(self) -> None:
        authority = ApprovalAuthority({"human-1": b"test-secret"})
        release = self.transition(from_state="HUMAN_APPROVAL", to_state="RELEASE", idempotency_key="release-1")
        with self.assertRaises(PolicyViolation): WorkflowGate({"checker"}).advance(release, NOW)
        approval = authority.issue("human-1", "run-1", HASH, "maker", 90, 110, "nonce-1")
        signed = dict(release, approval_receipt=approval)
        self.assertEqual(WorkflowGate({"checker"}, authority).advance(signed, NOW)["decision"], "ALLOW")
        forged = dict(approval, artifact_hash=DIST)
        with self.assertRaises(PolicyViolation): WorkflowGate({"checker"}, authority).advance(dict(release, approval_receipt=forged), NOW)
        expired = authority.issue("human-1", "run-1", HASH, "maker", 80, 99, "nonce-2")
        with self.assertRaises(PolicyViolation): WorkflowGate({"checker"}, authority).advance(dict(release, approval_receipt=expired), NOW)

    def test_budget_is_run_bound_concurrency_safe_and_holds_at_ceiling(self) -> None:
        ledger = BudgetLedger("run-1", "web-microgame", {"text_tokens": 100.0, "media_jobs": 2.0, "currency": 5.0, "wall_seconds": 60.0})
        with self.assertRaises(PolicyViolation): ledger.reserve("run-2", {"text_tokens": 1.0})
        decisions: list[str] = []
        lock = threading.Lock()
        def reserve() -> None:
            decision = ledger.reserve("run-1", {"text_tokens": 10.0})["decision"]
            with lock: decisions.append(decision)
        threads = [threading.Thread(target=reserve) for _ in range(20)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(decisions.count("ALLOW"), 10)
        self.assertEqual(decisions.count("HOLD"), 10)
        self.assertEqual(ledger.used["text_tokens"], 100.0)

    def asset(self, **updates):
        value = {
            "asset_id": "tree-01", "source_url": "https://example.invalid/tree",
            "license": "CC-BY-4.0", "scale_meters": 2.0, "up_axis": "Y",
            "poly_count": 5000, "poly_cap": 10000, "uv_sets": 1,
            "pbr_maps": ["base_color", "normal", "roughness", "metallic"],
            "lods": [0, 1], "collision": True, "engine_import_hash": HASH,
            "runtime_memory_mb": 12, "memory_cap_mb": 16,
            "frame_time_ms": 0.4, "frame_time_cap_ms": 0.8,
        }
        value.update(updates)
        return value

    def test_3d_asset_gate_rejects_semantic_and_schema_drift(self) -> None:
        self.assertEqual(validate_3d_asset(self.asset())["decision"], "READY")
        cases = [("uv_sets", 0), ("collision", False), ("license", "unknown"), ("scale_meters", 0), ("poly_count", 20000)]
        for field, value in cases:
            with self.subTest(field=field), self.assertRaises(PolicyViolation): validate_3d_asset(self.asset(**{field: value}))
        with self.assertRaises(PolicyViolation): validate_3d_asset(self.asset(unexpected=True))

    def test_policy_rejects_missing_or_unexpected_schema_fields(self) -> None:
        minimal = {"server_id": "engine-test", "server_version": "1.2.3", "allowed_tools": ["compile"], "project_root": self.root}
        with self.assertRaises(PolicyViolation): admit_tool_call(minimal, self.call, NOW, self.trusted_auth)
        extra = dict(self.policy, unexpected=True)
        with self.assertRaises(PolicyViolation): admit_tool_call(extra, self.call, NOW, self.trusted_auth)

    def test_canonical_hash_is_stable(self) -> None:
        self.assertEqual(canonical_hash({"b": 2, "a": 1}), canonical_hash({"a": 1, "b": 2}))

if __name__ == "__main__":
    unittest.main()
