#!/usr/bin/env python3
"""Validate the curated studio catalogs without network access."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTTPS = re.compile(r"^https://")
FILES = {
    "landscape-2026.json": ("sources", {"id", "kind", "name", "url", "license", "observed", "use", "limits"}),
    "mcp-gamedev-2026.json": ("servers", {"id", "stage", "url", "status", "capabilities", "risk"}),
    "workflow-budgets-2026.json": ("classes", {"id", "example", "duration", "text_tokens", "asset_jobs", "models", "skills", "mcp", "gates"}),
    "starlight-report-index-2026.json": ("reports", {"id", "date", "scope", "strength", "limitation", "source", "game_studio_use"}),
}

def main() -> int:
    errors: list[str] = []
    for filename, (array_key, required) in FILES.items():
        path = ROOT / "catalog" / filename
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{filename}: invalid JSON: {exc}")
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
            if "url" in row and not HTTPS.match(str(row["url"])):
                errors.append(f"{filename}[{index}]: url must be https")
            if filename == "workflow-budgets-2026.json":
                tokens = row.get("text_tokens", {})
                vals = [tokens.get(k) for k in ("lean", "likely", "premium")]
                if not all(isinstance(v, int) and v > 0 for v in vals) or vals != sorted(vals):
                    errors.append(f"{filename}[{index}]: token budgets must be positive lean<=likely<=premium integers")
    if errors:
        print(f"FAILED — {len(errors)} catalog problem(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Validated 4 studio catalogs: sources, MCP map, report index, and 5 workflow budgets.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
