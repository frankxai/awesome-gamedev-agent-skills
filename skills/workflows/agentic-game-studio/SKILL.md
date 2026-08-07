---
name: agentic-game-studio
description: >
  Orchestrates a governed multi-agent game-development slice from brief through playable evidence.
  Use when a request spans engine code, generated or DCC assets, MCP/CLI tools, multiplayer/backend,
  quality gates, budgets, or a release candidate; not for a small single-file game change.
license: Apache-2.0
compatibility: Engine-agnostic workflow; composes this repository's engine, discipline, genre, and shipping skills
metadata:
  engine: none
  category: workflow
  difficulty: advanced
---

# Agentic Game Studio

## Start contract

Before dispatching, write down: target player and platform; core loop; one vertical slice; engine and version; token/media budget; target hardware/network; kill criteria; evidence required. If the project already exists, fingerprint the engine with the router rather than guessing.

## Team shape

Use 3–5 roles: director/planner, gameplay engineer, technical-art/asset engineer, QA/performance engineer, and an independent verifier. Add specialists only when the slice requires them. Parallelize only independent files or tools.

## Execution

1. **Brief** — measurable player outcome and playable acceptance tests.
2. **Route** — load exactly one engine set plus relevant discipline, genre and workflow skills.
3. **Architect** — scene/state boundaries, save/network authority, performance budgets and failure modes.
4. **Manifest assets** — role, dimensions/scale, format, style, source/license, import contract and fallback.
5. **Build vertical slice** — code + data + assets + tests; placeholders first where possible.
6. **Close the tool loop** — mutate via approved MCP/CLI, compile/build, run/play, capture logs and screenshots, assert behavior.
7. **Verify fresh** — a reviewer who did not build checks gameplay, frame time, accessibility, safety, provenance and target-platform behavior.
8. **Gate** — PASS only with artifact evidence. Draft PR before any release; human approval for production, spend, stores and public actions.

## MCP rule

Skills explain; MCP/CLI tools act. Discover the live tool schema before invoking it. Treat editor/DCC execute-code tools as code execution, scope them to the project, and retain an operation receipt. See `../../../docs/MCP-GAMEDEV-ARCHITECTURE.md`.

## Budget rule

Choose a class from `../../../catalog/workflow-budgets-2026.json`; record text-token and media-job ceilings separately. Stop and re-scope before exceeding the ceiling.

## Done

Done means a runnable playable, automated checks, target-platform play evidence, asset/provenance manifest, independent verdict, known limitations and a rollback path. A design document, generated trailer, screenshot or agent self-report alone is not done.