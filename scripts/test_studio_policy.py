#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from studio_policy import BudgetLedger, PolicyViolation, WorkflowGate, admit_tool_call, canonical_hash, validate_3d_asset

HASH = "sha256:" + "a" * 64

class StudioPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = str(Path(self.tmp.name).resolve())
        self.policy = {
            "policy_version": "1.0.0", "server_id": "engine-test",
            "server_version": "1.2.3", "allowed_tools": ["compile", "capture"],
            "project_root": self.root, "allowed_egress_hosts": ["localhost"],
            "auth_required": True,
        }
        self.call = {
            "server_id": "engine-test", "server_version": "1.2.3", "tool": "compile",
            "project_root": self.root, "target_path": str(Path(self.root) / "game"),
            "egress_host": "localhost", "auth_expires_at": 200, "actor": "maker",
            "run_id": "run-1",
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_allowed_call_emits_hash_bound_receipt(self) -> None:
        result = admit_tool_call(self.policy, self.call, 100)
        self.assertEqual(result["admission"], "ALLOW")
        self.assertTrue(result["request_hash"].startswith("sha256:"))

    def test_unknown_tool_version_egress_auth_and_path_fail_closed(self) -> None:
        cases = [
            ("tool", "delete-project"), ("server_version", "0.0.1"),
            ("egress_host", "example.com"), ("auth_expires_at", 99),
            ("target_path", str(Path(self.root).parent / "escape")),
        ]
        for field, value in cases:
            call = dict(self.call); call[field] = value
            with self.subTest(field=field), self.assertRaises(PolicyViolation):
                admit_tool_call(self.policy, call, 100)

    def test_workflow_rejects_self_verification_duplicate_and_missing_human_gate(self) -> None:
        base = {
            "from_state": "PROTOTYPE", "to_state": "PLAYTEST", "actor": "maker",
            "verifier": "checker", "artifact_hash": HASH, "evidence_hashes": [HASH],
            "idempotency_key": "transition-1", "policy_version": "1.0.0",
        }
        gate = WorkflowGate()
        self.assertEqual(gate.advance(base)["decision"], "ALLOW")
        with self.assertRaises(PolicyViolation): gate.advance(base)
        self_approved = dict(base, idempotency_key="transition-2", verifier="maker")
        with self.assertRaises(PolicyViolation): gate.advance(self_approved)
        release = dict(base, from_state="HUMAN_APPROVAL", to_state="RELEASE", idempotency_key="transition-3")
        with self.assertRaises(PolicyViolation): gate.advance(release)

    def test_budget_is_concurrency_safe_and_holds_at_ceiling(self) -> None:
        ledger = BudgetLedger({"text_tokens": 100.0, "media_jobs": 2.0, "currency": 5.0, "wall_seconds": 60.0})
        decisions: list[str] = []
        lock = threading.Lock()
        def reserve() -> None:
            decision = ledger.reserve({"text_tokens": 10.0})["decision"]
            with lock: decisions.append(decision)
        threads = [threading.Thread(target=reserve) for _ in range(20)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(decisions.count("ALLOW"), 10)
        self.assertEqual(decisions.count("HOLD"), 10)
        self.assertEqual(ledger.used["text_tokens"], 100.0)

    def test_3d_asset_gate_rejects_missing_uv_collision_license_and_wrong_scale(self) -> None:
        asset = {
            "asset_id": "tree-01", "source_url": "https://example.invalid/tree",
            "license": "CC-BY-4.0", "scale_meters": 2.0, "up_axis": "Y",
            "poly_count": 5000, "poly_cap": 10000, "uv_sets": 1,
            "pbr_maps": ["base_color", "normal", "roughness", "metallic"],
            "lods": [0, 1], "collision": True, "engine_import_hash": HASH,
            "runtime_memory_mb": 12, "memory_cap_mb": 16,
            "frame_time_ms": 0.4, "frame_time_cap_ms": 0.8,
        }
        self.assertEqual(validate_3d_asset(asset)["decision"], "READY")
        for field, value in [("uv_sets", 0), ("collision", False), ("license", "unknown"), ("scale_meters", 0)]:
            malformed = dict(asset); malformed[field] = value
            with self.subTest(field=field), self.assertRaises(PolicyViolation):
                validate_3d_asset(malformed)

    def test_canonical_hash_is_stable(self) -> None:
        self.assertEqual(canonical_hash({"b": 2, "a": 1}), canonical_hash({"a": 1, "b": 2}))

if __name__ == "__main__":
    unittest.main()
