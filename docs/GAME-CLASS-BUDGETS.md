# Game-class model and token budgets

Planning estimates are in `catalog/workflow-budgets-2026.json`. Text tokens cover agent reasoning, code and review only. Generated images, video, voice and 3D are separate credit/GPU jobs; human playtesting is separate again.

## Routing by work shape

| Work | Model tier | Why |
|---|---|---|
| Discovery, source extraction, mechanical lint | fast/low-cost model | high volume, easy to verify |
| Game/system architecture, economy, netcode threat model | strongest reasoning model available | errors compound across the whole build |
| Scoped implementation and tests | strong coding model | tool use and patch quality matter more than prose |
| Screenshot/animation/3D review | multimodal model | must inspect pixels, motion and scene state |
| Release gate | independent frontier model/provider | maker must not grade itself |

Estate examples in August 2026 are Codex GPT-5.6 for implementation, a Claude Fable/Opus-class model for architecture/judgment, Gemini-class long-context/VLM work, and Grok-class adversarial/real-time checks. These are routing examples, not hard dependencies; pin exact models in a run receipt because names, limits and prices change.

## Interpretation

- Repeated whole-repo prompts waste tokens. Route only the engine + task + genre skills needed.
- The first playable should use placeholders or code-generated art. Spend media credits after the loop survives the delete test.
- Token budget is not a quality target. Quality comes from bounded slices, real execution and independent evidence.
- A premium 3D slice is expensive mainly because of integration and rework, not because one prompt is long.