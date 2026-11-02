---
name: author-setup
description: Interview the author and write the three author context files (author/who-i-am.md, how-i-talk.md, how-you-work.md) that every skill reads before writing text or acting on the author's behalf. Use on a fresh clone, when the Author says "set up", "start", "who am I", "настрой контекст", or when a skill finds author/ empty or stale.
---

# Author setup

The Editor writes captions, hooks and overlays in the author's voice and acts inside the author's rules. Those live in three files under `author/`, one per question the Editor keeps asking: who is this person, how do they talk, how do they want me to work. This skill fills them through a short interview. Adapted from the Cowork `cowork-setup` skill (see `docs/research/skills-review.md`).

Files and what each one feeds:

| File | Answers | Read by |
|---|---|---|
| `author/who-i-am.md` | who films, which Channel, which viewer, gear, cadence, current priority | `write-script` (audience, places), `style.json` review |
| `author/how-i-talk.md` | caption language, tone, signature phrases, example captions, what to avoid | `write-script` (hook, overlays, caption, hashtags) |
| `author/how-you-work.md` | how the Editor starts a task, shows results, what needs approval, how to push back | every skill, every session |

`author/` is personal and gitignored: it lives on this Mac only and never reaches the repo, which other people use too. On a fresh clone it does not exist; create it from `templates/` in this skill's folder before the first batch (`mkdir -p author && cp -n .claude/skills/author-setup/templates/*.md author/`). The templates carry the headings and the default hard rules.

## Rules of the interview

- Interview in the author's language (the one they write to you in). Write the files in that language too; quote captions in the language they are posted in.
- Ask with `AskUserQuestion`, 3–5 questions per batch, never more. After each batch, reflect the answers back in two or three lines, then write the file. Each file is written as soon as its batch is answered, never at the end.
- Use the author's own words. "Снимаю прогулки по городам на айфон" stays that way; it does not become "создаёт тревел-контент".
- Short answers are fine: write a lean file and leave a `<!-- add later -->` marker under the empty heading.
- If a file already exists, read it first and interview only about what is missing or what the author wants changed. Keep the rest untouched.
- If the author wants to see a file before it lands, show the draft and write it after a yes.

## Phase 1: who-i-am

Batch 1:
1. Who are you and what do you film? (How they would say it in one sentence.)
2. Which Channel is this for, and what is already posted there? (Handle, number of reels so far, what worked.)
3. Who is the one viewer you make these for? (One concrete person, not a demographic. This becomes `audience` in `style.json`.)
4. What do you film with? (iPhone model, Osmo, anything else.)

Batch 2:
5. How often do you walk and how many Reels do you want per Footage?
6. What is the one thing to get right this month? (The priority that resolves every "which first" question.)
7. Anything about schedule, where you live and travel, or who else is involved that the Editor should know? (Optional.)

Write `author/who-i-am.md`:

```markdown
# Who I am

## What I do
## The Channel
## The one viewer
## Gear
## Cadence
## Priority now
## Context
```

## Phase 2: how-i-talk

Batch 1:
1. What language are captions and overlays in? (One language, or a rule for when each is used.)
2. How do you talk in a caption: casual, dry, warm, blunt? Any words or openers that are very you?
3. Paste two or three real captions you are happy with. (These are the strongest signal; the Editor imitates them.)
4. What do you hate in captions and overlays? (Emoji, exclamation marks, "hidden gem", calls to "save this", whatever.)

Batch 2 (skip if the author wants to keep it short):
5. How should a hook sound: a question, a claim, a number, a confession? Examples of hooks you liked, yours or others'.
6. Hashtags and CTA: your own set, or let the Editor pick each time? Do you end with a CTA at all?

Write `author/how-i-talk.md`:

```markdown
# How I talk

## Language
## Tone
## Signature phrases
## Example captions
## Hooks I like
## Hashtags and CTA
## Never
```

The `Never` section is written as positive rules where possible ("captions end on the place name, no call to save") so `write-script` can copy them straight into its critique.

## Phase 3: how-you-work

Batch 1:
1. When you hand the Editor Footage, what should happen first: a plan to approve, a question or two, or straight to the first draft?
2. How do you want results shown: a shot list table, a sentence per decision, just the file path?
3. What must the Editor never do without asking? (Delete a Resolve project, re-render over a reviewed file, pick a Track, change `style.json`, spend money on a cloud service.)

Batch 2:
4. When the Editor thinks you are wrong about a cut or a hook, should it push back, suggest once, or do as told?
5. Anything else about working together? (Hours, "finish the Reel before asking", "one question at a time".)

Write `author/how-you-work.md`:

```markdown
# How you work

## Starting a task
## Showing results
## Ask before
## Pushback
## Also

## Hard rules
1. Nothing is published or uploaded anywhere.
2. A reviewed render is never overwritten; new renders get a new version suffix.
3. No paid cloud service is called; everything runs on this Mac (decision D1/D2 in docs/research/SYNTHESIS.md).
```

Keep the three hard rules even when the author did not mention them; add theirs below.

## Phase 4: wire up and finish

1. Confirm `CLAUDE.md` still carries the `## Author` section pointing at the three files. Restore it if someone removed it.
2. Update `style.json` `audience` from the one-viewer answer when it changed, and clear the "not yet reviewed by the author" status if the author confirmed the rest.
3. Tell the author which files were written and that any of them can be edited by hand or by asking; `how-you-work.md` is the control panel: when the Editor annoys them, the fix is a line there.

Done when all three files exist in `author/` with every heading either filled or marked `<!-- add later -->`, `git status` shows none of them, and `CLAUDE.md` points at them.
