# MCP architecture for game development

## Principle and implementation boundary

MCP servers are adapters, not the studio brain. The orchestrator owns state, gates and budgets; skills provide domain knowledge; MCP/CLI tools perform bounded actions; validators and humans decide promotion.

`catalog/mcp-gamedev-2026.json` is a **curated landscape**, not an executable admission registry. The standard-library reference core in `scripts/studio_policy.py` demonstrates fail-closed tool admission, project-root containment, hash-bound receipts, maker/checker separation and concurrency-safe budget ceilings. It is a contract testbed, not a production sandbox or MCP gateway.

```text
Brief/GDD -> router -> planner -> bounded makers -> engine/DCC adapters
                       |                  |
                       v                  v
                 asset manifest      builds/logs/captures
                       \                  /
                        verifier + evidence ledger
                                  |
                         preview/release gate
```

## Adapter classes

| Class | Examples | Game-development use | Mandatory control |
|---|---|---|---|
| Engine authoring | Unity, Godot, Unreal MCP/CLI | scenes, scripts, assets, play mode, builds | discover tools; pin engine/plugin; project-path allowlist |
| DCC authoring | Blender, TouchDesigner, future Maya/Houdini/Substance | meshes, rigs, materials, VFX, animation | sandbox; file manifest; export/import proof |
| Generative media | Higgsfield, ComfyUI, Meshy | concepts, sprites, textures, video, audio, 3D | model contract; seed/job receipt; rights/provenance; visual QA |
| Multiplayer/backend | Rivet patterns, Supabase, Railway | matchmaking, persistence, telemetry, services | server authority; schema/migration gate; cost limits |
| QA/observability | Playwright, Sentry, engine test runner | input flows, screenshots, crashes, traces | no logged-in ambient browsing; retain failing evidence |
| GitOps/release | GitHub, Vercel/Railway, stores | PRs, previews, CI, deployment | draft first; no unattended merge/promotion |

## Closed loops

### Browser microgame
Router → `phaser-core`/`pixijs-rendering` + `game-feel` → coding agent → local build → Playwright keyboard/touch flows → screenshots → vision reviewer → draft PR. Higgsfield is optional for art; code-generated primitives are preferred for the first playable.

### Godot 2D vertical slice
Router → Godot + genre/discipline skills → asset manifest → Higgsfield/ComfyUI batch → VIS provenance → Godot MCP/CLI import and scene wiring → headless tests + real-device play → performance/craft reviewers → gate record.

### Networked Unity/Unreal 3D slice
Architecture reviewer → server-authority threat model → Unity/Unreal live-editor adapter → Blender/Meshy asset lane → Rivet/backend lane → deterministic simulation tests → latency/packet-loss/soak tests → VLM scene review → independent security/performance gate.

### Premium cinematic content lane
Art director → shot/asset manifest → Higgsfield/ComfyUI concept generation → Meshy/Blender/USD assembly → engine import → lighting/animation → capture → continuity and rights review. Generated video may sell the idea, but cannot substitute for a playable engine build.

## 3D definition of done

A URL to a mesh is not a game asset. Require: source and license; coordinate system and real-world scale; topology/poly budget; UVs and PBR textures; material slots; pivot/origin; rig and animation naming; LODs; collision/nav proxy; engine import preset; render screenshot; in-engine frame-time and memory evidence.

## Security baseline

- Treat arbitrary Python/C#/Blueprint execution as code execution.
- Keep MCP local unless remote auth and tenancy are explicit.
- Use least-privilege tool lists and project-root allowlists.
- Preserve operation and generated-asset manifests.
- Never expose credentials in prompts, repos or model context.
- Builders cannot self-approve release gates.

Machine-readable landscape notes: `catalog/mcp-gamedev-2026.json`. Admission and transition schemas live in `contracts/`.