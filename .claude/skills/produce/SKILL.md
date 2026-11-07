---
name: produce
description: Produce a Video with project-local video-* agents. Routes by Format (Walk Reel, Meme cut, Tech explainer, Travel long, freeform motion), launches the chain, puts author questions to the user. Use when the author asks to make, finish, or continue a Video, Reel, explainer, or motion piece — not for research-only or Desk-only tasks.
disable-model-invocation: false
---

# Produce a Video

You are the **producer** (main session). You talk to the author and launch `.claude/agents/video-*`. You do not gather context, plan, edit files or review artifacts yourself. Contract: `docs/agents/video-chain.md`. Terms: `GLOSSARY.md`.

## 1. Fix Format and chain

From the ask, `video.json` / Reel path, or `formats/<id>/FORMAT.md`:

| Format / ask | Chain |
|---|---|
| Walk Reel, vertical walk from Footage | Walk (material-first) |
| Meme cut | Walk (material-first; picture uses `/meme-cut`) |
| Tech explainer, Remotion/HyperFrames motion, code graphics | Motion (script-first, VO before picture) |
| Travel long | Hybrid — planner names phase scope |
| Ambiguous | Stop; present both routes to the author |

If Format is still unclear after one clarifying question, stop (`NEEDS_INPUT`).

## 2. Launch planner

Launch `video-planner` with: the ask, Format guess, Video/Footage paths if known, and "return Assumptions, Questions for the user, Simpler alternative, chosen chain, acceptance criteria, first maker".

When Questions or Simpler alternative are not `none`, put them to the author (with Assumptions) before any maker. Send answers that change the plan back to the same planner. When both are `none`, continue.

## 3. Run the chain

Follow the planner's chain and `docs/agents/video-chain.md`. Default hop budget 3 unless the author named a phase scope.

For each hop:

1. Launch the next `video-*` maker with the plan slice, paths, visited set, and scratch folder.
2. On `NEEDS_INPUT` / `BLOCKED`, stop and report to the author.
3. On `DONE`, record the agent in the visited set; do not relaunch it in this chain.
4. After the finishing maker (or when the plan says check now), launch `video-checker`.
5. Blocking findings → same maker (max 2 rounds), then checker again. Then report to the author.

Makers must invoke the **skills** named in the chain table (e.g. `/write-script`, `/build-reel`), not reinvent steps. Motion makers read `overlays/CLAUDE.md`.

## 4. Outward actions

`cf.publish`, push, PR, issue comments: only when the author explicitly asked in this session. Pass that command to `video-finish` (or refuse if the hop is not finish). Never publish as an automatic hop.

## 5. Report to the author

After a clean checker verdict (or a stop), report: Format, chain, artifacts written, checker `Verdict:` line, open loops, `recommended_next_agent` if blocked on budget alone.

## Single-step bypass

If the author names one skill only (e.g. "only ingest this folder"), run that skill in the main session or one matching maker — do not force a full chain. Still use `video-checker` when the step writes `script.json`, a timeline or a render.
