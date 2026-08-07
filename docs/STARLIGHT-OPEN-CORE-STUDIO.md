# Starlight open-core game studio

## Product topology

One substrate, multiple brands:

| Layer | Name | Public/open | Private/commercial |
|---|---|---|---|
| Knowledge | awesome-gamedev-agent-skills | engine/genre/workflow skills, router, source catalog | none |
| Studio core | Starlight Game Studio | workflow schema, adapters, validators, evidence contracts, example projects | hosted control plane, private connectors, portfolio telemetry |
| Creator product | GenCreator Game Studio | selected templates/SDK | guided generation UX, asset library, collaboration, credits/billing |
| Universe vertical | Arcanea Game Studio | canon-safe sample packs where publishable | locked canon, unreleased stories/assets, commercial game IP |
| Portfolio operator | FrankX App Studio/Forge | selected methods after hardening | strategy, budgets, product bets, store operations |

“Kenyan Game Development Studio” is not introduced as a brand without a deliberate identity/market decision. If the phrase was dictation for **Arcanean**, the Arcanea vertical above is the intended role.

## Open-core boundary

Open: portable skills, registries, schemas, validators, sample adapters, benchmark scenarios, local-first orchestration contracts.

Commercial/private: hosted generation credits, proprietary asset libraries, unpublished canon, licensed DCC integrations, portfolio analytics, store credentials, paid MCP endpoints and production promotion.

## Multi-agent team

Use the smallest 3–5 roles per slice, not a standing 19-agent fan-out:

1. **Director/planner** — locks scope, budget, kill criteria and evidence.
2. **Gameplay engineer** — owns the vertical slice.
3. **Asset/technical-art engineer** — owns manifests and engine-ready imports.
4. **QA/performance engineer** — tests on target hardware/network.
5. **Independent verifier** — did not build; signs pass/fail.

Add narrative, economy, backend, security or liveops specialists only when the slice needs them. Every dispatch has one question, exact files, a done condition and a token/tool budget.

## Workflow state machine

`DISCOVER → BRIEF → ARCHITECT → ASSET_MANIFEST → PROTOTYPE → PLAYTEST → HARDEN → RELEASE_CANDIDATE → HUMAN_APPROVAL → RELEASE → LIVEOPS`

Each transition requires a receipt. A text report without a playable or validated artifact cannot advance `PROTOTYPE` or later.

The structural reference contracts cover tool admission, workflow transitions, signed approvals, and asset readiness. `scripts/studio_policy.py` is explicitly a non-production, process-local example that tests fail-closed behavior: revocation and exact distribution/tool admission, trusted authorization adapters, path and egress containment, hash-bound evidence, trusted maker/checker separation, artifact/run-bound HMAC approval verification, idempotency, and atomic budget `HOLD`. It does **not** claim to provide an OS sandbox, authenticated policy distribution, persistent workflow/budget ledger, live engine adapters, or recovery orchestration; those remain production admission requirements.

## Adoption plan

1. Keep this fork close to upstream; contribute general improvements upstream.
2. Add orchestration/evidence extensions without copying vendor skill text.
3. Pilot with a browser microgame, then a Godot 2D slice, then a networked 3D slice.
4. Only after those benchmarks pass should private FrankX Forge absorb adapters and gates.
5. Retire or redirect the legacy Arcanea game skills; do not maintain competing routers.