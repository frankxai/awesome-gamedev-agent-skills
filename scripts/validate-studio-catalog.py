#!/usr/bin/env python3
"""Validate studio catalogs, packaging parity, contracts, and optional source reachability."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from studio_policy import ApprovalAuthority, ASSET_FIELDS, POLICY_FIELDS, TRANSITION_FIELDS

ROOT = Path(__file__).resolve().parents[1]
HTTPS = re.compile(r"^https://")
COUNT = 67
MCP_STATUSES = {"reference", "candidate", "evaluate", "watch"}
SOURCE_DECISIONS = {"reference", "evaluate", "adopted"}
PRIVATE_MARKERS = {"installed", "available-local-skill", "internal-installed"}
FILES = {
    "landscape-2026.json": ("sources", {"id", "kind", "name", "url", "license", "decision", "retrieved_at", "observed", "use", "limits"}),
    "mcp-gamedev-2026.json": ("servers", {"id", "stage", "url", "status", "capabilities", "risk"}),
    "workflow-budgets-2026.json": ("classes", {"id", "example", "duration", "text_tokens", "asset_jobs", "models", "skills", "mcp", "gates"}),
    "starlight-report-index-2026.json": ("reports", {"id", "date", "scope", "strength", "limitation", "source", "game_studio_use"}),
}
CONTRACTS = {"tool-admission.schema.json", "workflow-transition.schema.json", "asset-readiness.schema.json", "approval-receipt.schema.json"}
RUNTIME_CONTRACT_FIELDS = {
    "tool-admission.schema.json": (POLICY_FIELDS, POLICY_FIELDS - {"revoked"}),
    "workflow-transition.schema.json": (TRANSITION_FIELDS, TRANSITION_FIELDS - {"approval_receipt"}),
    "asset-readiness.schema.json": (ASSET_FIELDS, ASSET_FIELDS),
    "approval-receipt.schema.json": (ApprovalAuthority.FIELDS, ApprovalAuthority.FIELDS),
}


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return None


def validate_packaging(errors: list[str]) -> None:
    manifest = load_json(ROOT / ".claude-plugin" / "marketplace.json", errors)
    if manifest is None:
        return
    discovered = {"./" + path.parent.relative_to(ROOT).as_posix() for path in (ROOT / "skills").rglob("SKILL.md")}
    if len(discovered) != COUNT:
        errors.append(f"discovered {len(discovered)} skills; expected {COUNT}")
    plugins = {plugin["name"]: plugin for plugin in manifest.get("plugins", [])}
    all_bundle = set(plugins.get("gamedev", {}).get("skills", [])) - {"./router"}
    if all_bundle != discovered:
        errors.append(f"gamedev plugin parity mismatch: missing={sorted(discovered-all_bundle)} extra={sorted(all_bundle-discovered)}")
    workflows = {item for item in discovered if item.startswith("./skills/workflows/")}
    workflow_bundle = set(plugins.get("workflows", {}).get("skills", []))
    if workflow_bundle != workflows:
        errors.append(f"workflow plugin parity mismatch: missing={sorted(workflows-workflow_bundle)} extra={sorted(workflow_bundle-workflows)}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if f"**{COUNT} game-dev skills**" not in readme or f"{COUNT} skills across" not in readme:
        errors.append("README skill count is out of sync")


def validate_contracts(errors: list[str]) -> None:
    for filename in CONTRACTS:
        data = load_json(ROOT / "contracts" / filename, errors)
        if data is None:
            continue
        if data.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{filename}: must declare JSON Schema 2020-12")
        required = data.get("required")
        if not isinstance(required, list) or not required:
            errors.append(f"{filename}: required must be non-empty")
            continue
        runtime_properties, runtime_required = RUNTIME_CONTRACT_FIELDS[filename]
        schema_properties = set(data.get("properties", {}))
        if schema_properties != runtime_properties:
            errors.append(f"{filename}: schema/runtime property drift: schema={sorted(schema_properties)} runtime={sorted(runtime_properties)}")
        if set(required) != runtime_required:
            errors.append(f"{filename}: schema/runtime required-field drift: schema={sorted(required)} runtime={sorted(runtime_required)}")


def check_url(item_id: str, url: str, errors: list[str]) -> None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "awesome-gamedev-catalog-validator/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status >= 400:
                errors.append(f"{item_id}: HTTP {response.status} {url}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        errors.append(f"{item_id}: unreachable {url}: {type(exc).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", action="store_true", help="also verify current HTTP reachability")
    args = parser.parse_args()
    errors: list[str] = []
    for filename, (array_key, required) in FILES.items():
        data = load_json(ROOT / "catalog" / filename, errors)
        if data is None:
            continue
        rows = data.get(array_key)
        if not isinstance(rows, list) or not rows:
            errors.append(f"{filename}: {array_key} must be a non-empty list")
            continue
        ids: set[str] = set()
        for index, row in enumerate(rows):
            missing = required - set(row)
            if missing:
                errors.append(f"{filename}[{index}]: missing {sorted(missing)}")
            item_id = row.get("id")
            if not isinstance(item_id, str) or not item_id:
                errors.append(f"{filename}[{index}]: invalid id")
            elif item_id in ids:
                errors.append(f"{filename}: duplicate id {item_id}")
            else:
                ids.add(item_id)
            if "url" in row:
                url = str(row["url"])
                if not HTTPS.match(url):
                    errors.append(f"{filename}[{index}]: url must be https")
                elif args.network:
                    check_url(str(item_id), url, errors)
            if filename == "mcp-gamedev-2026.json":
                status = row.get("status")
                if status not in MCP_STATUSES:
                    errors.append(f"{filename}[{index}]: status {status!r} not in {sorted(MCP_STATUSES)}")
                if status in PRIVATE_MARKERS:
                    errors.append(f"{filename}[{index}]: public catalog leaks private availability")
            if filename == "landscape-2026.json":
                decision = row.get("decision")
                if decision not in SOURCE_DECISIONS:
                    errors.append(f"{filename}[{index}]: invalid decision {decision!r}")
                if decision == "adopted" and (row.get("license") in {"unknown", "NOASSERTION"} or not row.get("revision")):
                    errors.append(f"{filename}[{index}]: adopted source requires known license and pinned revision")
            if filename == "workflow-budgets-2026.json":
                tokens = row.get("text_tokens", {})
                values = [tokens.get(key) for key in ("lean", "likely", "premium")]
                if not all(isinstance(value, int) and value > 0 for value in values) or values != sorted(values):
                    errors.append(f"{filename}[{index}]: token budgets must be positive lean<=likely<=premium integers")
    validate_packaging(errors)
    validate_contracts(errors)
    if errors:
        print(f"FAILED — {len(errors)} problem(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    suffix = " with network source checks" if args.network else ""
    print(f"Validated 4 catalogs, {COUNT}-skill package parity, and 4 contracts{suffix}.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
