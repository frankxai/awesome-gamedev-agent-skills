# Game-development agent landscape — 2026-08-07

## Verdict

The ecosystem has crossed from prompt packs into **tool-using production systems**, but no single open repository combines all six layers: version-pinned engine knowledge, live editor control, generated-asset pipelines, multiplayer/backend operations, deterministic QA, and governed multi-agent delivery. This repository is strongest at the first layer and is a good neutral public substrate.

The Starlight estate is broad but uneven: the 2026-06-26 capability audit counted **613 skills and 901 lint findings**; 587 lacked an OpenAI metadata file, 126 exceeded the local length threshold, and 114 had invalid names. A keyword slice found 185 game/media/3D/MCP/agent-related entries, but only 20 were clean under that older rubric. The 2026-08-07 repo inventory counted 164 local Git repos and 353 GitHub repos, with average local hygiene 53.8/100, 61 with tests, 85 with CI, and 52 dirty. These are inventory signals, not a full semantic quality grade.

## What is genuinely strong locally

- `frankx-app-forge` has a coherent 19-agent/12-skill team, staged gates, fresh-context review, vertical slices, ethical monetization and explicit machine-zone discipline.
- Higgsfield skills are operational rather than decorative: model discovery, job submission, retries, asset manifests and handoff contracts. The game-generation skill covers browser-game images, sprites, textures, audio and 3D, then hands build/deploy to Higgsfield Websites.
- ComfyUI and TouchDesigner skills include executable scripts, health checks, API contracts and hard-won pitfalls.
- The internal MCP registry already models trust, action tier, human gates, version policy and per-host availability.

## Main weaknesses

1. **Coverage is not integration.** Many capable skills are adjacent, but the game build loop does not yet bind engine MCP, asset generation, provenance, playtest evidence and release gates into one executable state machine.
2. **Private studio is narrow.** Its game architect is Godot/mobile-centric. It lacks Unity/Unreal/Roblox/web selection, DCC/3D import contracts, multiplayer/load-test architecture and token/asset budgets.
3. **Skill hygiene debt is large.** The older lint report is dominated by packaging and duplication problems; high skill count overstates ready-to-route capability.
4. **Claims exceed evidence in some legacy skills.** “AAA” labels and premium assertions often lack runnable evaluators, sample projects or benchmark receipts.
5. **MCP is a trust boundary.** Editor and DCC servers can run code or mutate binary assets. Popularity does not make them safe.
6. **Vendor catalogs are volatile.** During this audit, `higgsfield-game-generation` remained indexed on skills.sh with 26,585 installs while its directory disappeared from the vendor repository's current `main` after a new push. Pin reviewed revisions; never route production work from a floating marketplace entry.

## Maturity rubric

Score each capability 0–5 on: provenance/versioning; trigger/routing precision; executable tooling; deterministic validation; runtime/editor integration; safety/governance; evidence from real outputs.

| System | P/V | Route | Exec | Validate | Runtime | Safety | Evidence | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Upstream 66-skill library | 5 | 5 | 2 | 4 | 1 | 3 | 3 | **3.3** |
| FrankX App Forge team | 4 | 4 | 3 | 3 | 2 | 5 | 2 | **3.3** |
| Higgsfield game/media skills | 4 | 4 | 5 | 3 | 3 | 4 | 4 | **3.9** |
| ComfyUI local skill | 5 | 5 | 5 | 5 | 4 | 4 | 5 | **4.7** |
| TouchDesigner MCP skill | 5 | 5 | 5 | 5 | 5 | 4 | 5 | **4.9** |
| Legacy Arcanea game skills | 1 | 2 | 1 | 1 | 1 | 2 | 0 | **1.1** |
| Internal MCP registry | 4 | 4 | 4 | 4 | 4 | 5 | 4 | **4.1** |

These scores are review judgments based on inspected artifacts, not benchmark results.

## State-of-the-art patterns worth absorbing

- **Portable, version-pinned skills + minimal router** — this upstream repository.
- **Official live-editor CLI and MCP discovery** — Unity’s `unity status` / command discovery pattern avoids guessing scene commands.
- **Closed tool loop** — editor change → compile → run/play mode → logs → screenshot → assertion.
- **Manifest-first media generation** — Higgsfield’s asset CSV and stable style formula.
- **Game-ready 3D contract** — generation is only the start; enforce scale, topology, UV/PBR, rig, animation, LOD, collision, naming, license and engine-import checks.
- **Authoritative multiplayer simulation** — Rivet’s separation of client prediction, server validation, matchmaking and interest management.
- **USD/VLM content agents** — NVIDIA’s material/physics/texture automation suggests a scalable 3D validation lane.
- **Fresh-context maker/checker** — builders do not grade their own work; evidence gates stop the line.

## Brand decision

Do not create three competing studio substrates. Use one technical core and three surfaces:

- **Starlight Game Studio** — open-core engine, orchestration contracts, validators and MCP adapters.
- **GenCreator Game Studio** — creator-facing product for rapid web/mobile game generation and reusable asset workflows.
- **Arcanea Game Studio** — flagship universe/content vertical using locked Arcanea canon, not a separate infrastructure stack.

The existing private **FrankX App Studio/App Forge** remains the portfolio operator and premium mobile distribution layer; it should consume the public core rather than duplicate it.

See `catalog/landscape-2026.json` for the source register.