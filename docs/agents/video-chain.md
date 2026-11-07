# Video production chain

Handoff contract for multi-agent Video work in this repo. The main session is the **producer**: it talks to the author, launches `.claude/agents/video-*`, and does not gather context, plan, edit or review itself. Workers invoke existing skills; agents are roles. Router skill: `/produce`. Vocabulary: `GLOSSARY.md`. Dry-run routing examples: `docs/agents/video-chain-smoke.md`.

## Unit of work

One **Video** (`videos/<slug>/` or a Walk Reel under Footage until migrated — ADR 0006). Lifecycle lives in `video.json` (or the Reel folder). Not a GitHub issue per shot.

## Agents

| Agent | Edits | Role |
|---|---|---|
| `video-context` | no | Read-only lookups |
| `video-planner` | no | Format, chain, plan, author questions |
| `video-writer` | yes | Script / voice-over / caption text |
| `video-footage` | yes | Ingest, shotlog, clip cards |
| `video-picture` | yes | Cuts, Resolve, meme-cut |
| `video-motion` | yes | Remotion / HyperFrames / overlays kit |
| `video-sound` | yes | Track, VO, beds, caption timing |
| `video-finish` | yes | Render, verify, stage publish |
| `video-checker` | no | Schema, continuity, render-check; veto |

`video-planner` may launch only `video-context`. Other makers launch no agents. Research contour (`/research-map`) is named by the planner when needed; there is no always-on researcher.

## Chains

### Walk Reel / Meme cut (material-first)

`video-planner` → `video-footage` → `video-writer` → `video-sound` (if a Track or VO is in scope) → `video-picture` → `video-finish` → `video-checker`

| Hop from | Artifact in | Artifact out | Skill |
|---|---|---|---|
| footage | raw folder | `clip_manifest.json`, proxies | `/ingest-footage` |
| footage | proxies | `shotlog/*.json` | `/analyze-clips` |
| writer | shotlogs | `script.json` | `/write-script` |
| sound | script + Track | `cuts.json` (beat grid) | `/beat-grid` |
| picture | script (+ cuts) | Resolve timeline / meme MP4 | `/build-reel`, `/meme-cut` |
| finish | timeline | `out/*.mp4` + checks | `/render-reel` |

Walk Reel text overlays stay on `/build-reel` + `overlays/Overlay.tsx`, not freeform motion.

### Tech explainer / freeform motion (script-first)

`video-planner` → `video-writer` → `video-sound` (**VO first**; timing drives picture) → `video-motion` → `video-finish` → `video-checker`

| Hop from | Artifact in | Artifact out | Skill / kit |
|---|---|---|---|
| writer | `brief.md` | `script.*`, `voiceover.md` | `/write-script` or Format rules |
| sound | voiceover text | audio + word times | Chatterbox (`.venv-chatterbox`) or author VO; stable-ts |
| motion | timed VO + brief | Remotion / HyperFrames under Video or `overlays/` | `overlays/CLAUDE.md`, Remotion / HyperFrames skills |
| finish | composition | `renders/` + checks | Remotion/HyperFrames render; stage via `cf.publish` only on author ask |

### Travel long (hybrid)

Same agents. Planner names a phase scope (footage chapters + scripts + Remotion map beats). Author-gated phase scope overrides the default hop budget below.

## Handoff budget

Default: **3 automatic handoffs** after the originating agent in one unattended chain. Count only automatic edges. Operator-gated steps (publish, spend, delete) and skills invoked as a subroutine of another agent are not hops.

An author go that names the phases it covers (for example "footage through render for this Walk Reel") sets the budget to that chain's length for that run; the handoff record quotes it. Visited set and stop conditions still apply.

## Visited set

Carry the set of agents already run in this chain. **Never run the same agent twice** in one chain. On a loop, name the skipped agent and ask the author; missing inputs from the first pass are not new evidence for a silent rerun.

## Stop conditions (outrank the budget)

Halt and hand back to the producer when any fires:

| Condition | Why |
|---|---|
| Missing authority | Next step needs a permission this request never granted |
| Material fork | An assumption would change truth, cost or reversibility |
| External side effect | Publish, spend, delete, or any outward action |
| Ambiguous route | Two Formats or successors are similarly plausible |
| Inputs absent | Successor's required artifacts do not exist yet |
| Schema / continuity fail | `video-checker` veto — blocking findings |

Ambiguity is a stop, not a coin-flip. Present both routes.

## Stopping report

A mid-pipeline stop is normal. The returning agent reports:

- **status** — `DONE` · `DONE_WITH_CONCERNS` · `BLOCKED` · `NEEDS_INPUT`
- **recommended_next_agent** — successor by name (even when budget alone stops an otherwise-ready hop)
- **open_loops** — what remains, visited chain, stop reason
- **evidence** — each finding labelled **Measured · User-provided · Calculated · Estimated · Proxy · Unknown**

## Checker and loops

`video-checker` does not fix. It ends with:

`Verdict: <clean|findings|inconclusive>; artifact: <path-or-sha>; blocking: n; non-blocking: m`

plus a non-empty `Verified:` list of checks it ran. Clean requires no blocking findings and no required check left in `Not run:`.

Producer loops: maker ↔ checker at most **2** rounds; then stop and report to the author. After every fix, checker runs again before the producer reports clean.

## Progress

Each maker and checker keeps `progress.md` in the scratch folder named in its prompt: done, next, open problems, last artifact path. A successor of the same role continues from that file; the producer stops listed background tasks first.
