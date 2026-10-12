# 09 · Storytelling structures that hold attention

Source: ChatGPT Deep Research, downloaded by the author on 2026-10-12 (`~/Downloads/deep-research-report (6).md`). ChatGPT's inline citation markers (416 of them) did not export as links and were stripped; only the claims and the sources named in the text remain. The Opus agent run of the same prompt is `result-a.md`.

---

# Storytelling Structures for Long-Form and Short-Form Video

## Evidence key and research conclusions

The most important result is that **there is no single evidence-backed “YouTube story structure.”** YouTube itself measures the outcome—where viewers continue, leave, skip, rewatch, or share—but does not prescribe three acts, a re-hook interval, a number of open loops, or a mandatory climax position. YouTube’s audience-retention report defines the first 30 seconds as the “intro,” identifies later “top moments,” spikes and dips, and explicitly recommends moving compelling later material earlier when appropriate. It also compares a video against recent videos of similar length rather than publishing one universal retention benchmark. **[DATA]**

The strongest creator evidence points to a smaller set of mechanisms that can sit inside many different frameworks:

**promise confirmation → forward question → causal progression → changing state/stakes → partial resolution → escalation/new information → satisfying payoff.** This is a synthesis of MrBeast’s internal production logic, Johnny Harris’s first-person description of packaging and foreshadowing, Veritasium’s experimentally informed misconception treatment, Parker/Stone’s causal “but/therefore” rule, and YouTube’s own retention diagnostics. **[PRACTITIONER]**

A second important result is negative: some supposedly canonical creator frameworks are much less verified than creator-advice culture implies. In particular, I did **not** find strong evidence that top YouTubers literally outline with Dan Harmon’s story circle or Joseph Campbell’s hero’s journey. Those frameworks can describe a finished challenge or transformation video after the fact, but that is different from evidence that the creator actually used the framework. **[PRACTITIONER]** Dan Harmon himself is a verified user of his eight-stage circle, but that verifies the framework for his television writing, not for YouTube.

Johnny Harris is an especially useful falsification case. In a March 2025 deep interview about his writing process, he explicitly says he does **not** identify with classical rising-action/climax formulas, has “never” had a standard act structure, and does not believe there is an ultimate structure humans require. What he *does* consciously use is a packaging promise, an obligation to answer it by the end, first-minute reinforcement of the promise, extensive research, visual scripting and natural foreshadowing. Thus **“question → journey → answer” is a useful descriptive compression of Harris, not his declared formula. [PRACTITIONER]**

Likewise, MrBeast’s “every minute better than the last” should not become a universal agent rule. His leaked production guide emphasizes the first minute, explicit responsibilities for later time ranges, “wow” moments and re-engagement/escalation; analysis of the guide reports new rules or escalation around roughly three and six minutes. But by late 2025 Donaldson was publicly discussing a shift toward more story- and emotion-focused content as audiences became accustomed to pure scale and spectacle. **[PRACTITIONER]**

For the agent, I would therefore implement **mechanisms first, framework second**:

| Agent concept | Status | What it means |
|---|---|---|
| `packaging_promise` | **Core** | What title/thumbnail/opening implicitly or explicitly promises. **[DATA]** YouTube says strong first-30-second retention can indicate that the opening matched thumbnail/title expectations. |
| `primary_question` | **Core when applicable** | The unresolved outcome, answer or change the viewer expects. **[PRACTITIONER]** Harris deliberately defines a promise he knows he must answer. |
| `causal_chain` | **Core** | Each beat should change what follows rather than merely sit beside it. **[PRACTITIONER]** Parker/Stone explicitly test beats with “but” or “therefore.” |
| `state_change` | **Core** | Every major beat should alter knowledge, progress, stakes, constraints, options or emotional state. **[PRACTITIONER]** This is the useful generalization behind escalation frameworks. |
| `mini_payoff` | **Useful, not mandatory cadence** | Resolve a local question while the main one remains alive. **[PRACTITIONER]** |
| `main_payoff` | **Core** | Satisfy the promise rather than merely ending the video. **[PRACTITIONER]** Harris explicitly says the promised question must be answered by the end. |
| `open_loop_count` | **Diagnostic, not algorithm rule** | Number of simultaneously unresolved questions. No platform source establishes an optimum. **[PRACTITIONER]** |
| `act_structure` | **Optional** | Useful for organization, not a YouTube law. **[PRACTITIONER]** Harris explicitly rejects an obligatory classical structure. |
| `hero_journey` / `story_circle` | **Optional story model** | Good for personal quests and transformations, poor as a universal validator. **[THEORY]** |
| `retention_drop_prediction` | **Do not fake** | A script can flag probable friction, but actual retention is only measurable after viewers watch. **[DATA]** YouTube Analytics provides observed retention at video level. |

**Source-quality caveat.** The best hard measurement available here is YouTube’s own definition of retention behavior and Derek Muller’s controlled multimedia-learning work. The MrBeast production guide is unusually valuable tier-two material but was leaked rather than formally published; its practices should therefore be treated as MrBeast-team practice, not platform doctrine. Johnny Harris’s evidence is unusually strong first-person practitioner evidence because he walks through actual scripts, production stages and named videos in detail. 1of10 and Sandcastles provide useful current format/outlier practice, but public claims such as “this format is producing outliers” are **PRACTITIONER**, not **DATA**, unless the underlying sample is shown.


## Table A — Frameworks

| Framework | Who demonstrably uses it / validation | Beat model for the agent | Evidence | Concrete example + timestamps | Best fit |
|---|---|---|---|---|---|
| **Packaging promise → investigation → answer → reflection** | **Johnny Harris: verified in substance, but not as a named formula.** Harris says he often tests two or three packaging options before committing, treats packaging as a clear promise, must answer that promise by the end, reinforces it within roughly the first minute, and naturally foreshadows what is coming. He explicitly rejects a universal classical act formula. | `promise → why_this_matters → evidence/journey → complication → evidence → answer → zoom_out` | **PRACTITIONER.** First-person 2025 process walkthrough. | Harris discusses **“Why Saudi Arabia Is Building a $1 Trillion City in the Desert”** at [10:15–13:13 of this interview](https://www.youtube.com/watch?v=zq4b96m1AvM&t=615s): packaging/promise at ~10:15–11:21; obligation to answer it ~11:23–13:06; reinforce promise in first minute ~13:06–13:13. These timestamps document his construction of that named video rather than constituting retention data. | 8–40 min investigations, history, geopolitics, case studies. Can compress to 60 s–3 min. |
| **Misconception → prediction/commitment → cognitive conflict → explanation → corrected model** | **Veritasium: unusually well validated.** Muller’s research found misconception/refutation and dialogue treatments generated greater learning gains than straightforward exposition; his publications describe showing alternative conceptions to expose inconsistencies. This validates learning, **not YouTube retention**. | `familiar_belief → test_question → viewer_commitment → surprising_result → why_intuition_fails → model → transfer_test` | **DATA — learning, not retention.** Controlled multimedia research; **PRACTITIONER** for its application to Veritasium. | **Veritasium, “The Biggest Misconception About Electricity”**: [0:03](https://www.youtube.com/watch?v=bHIhgxav9LY&t=3s) introduces the extreme circuit thought experiment; around [0:48](https://www.youtube.com/watch?v=bHIhgxav9LY&t=48s) asks the viewer to commit to an answer and explicitly delays resolution. Independent transcript coding identifies those same beats. | 5–20 min explainers; excellent when the audience probably holds an intuitive wrong model. |
| **Stakes → escalation → payoff / novelty ladder** | **MrBeast: verified team practice.** The leaked production guide assigns different jobs to successive portions of a video, stresses the first minute and “wow factor,” while reporting from the guide describes deliberate re-engagement/escalation later. | `promise/stakes → immediate action → harder/bigger/new constraint → mini_payoff → escalation → reversal → largest meaningful payoff` | **PRACTITIONER** for the structure; internal numerical retention statements are **DATA-like internal measurements**, but not independently replicated. | **MrBeast, “$1 vs $500,000 Plane Ticket!”**: 0:00 states the $500k endpoint; 0:11 starts at the cheapest plane; 1:22 $1k; 2:10 $10k; 3:08 $25k; 4:31 $100k; 7:02 $300k blimp; 9:40 reaches the headline $500k plane; 10:26 opens a new sub-loop; 11:56 adds a destination surprise before ending. The transcript shows literal escalating price/stakes tiers. | Challenges, comparisons, builds, travel and spectacle; 8–40+ min. Also compressible to Shorts. |
| **But / therefore causal spine** | **Trey Parker & Matt Stone: directly verified for South Park’s writers’ room.** They say they write beats on a wall and test that the relationship is “but” or “therefore,” rejecting sequences connected only by “and then.” I found no comparably strong evidence that a named top YouTuber literally runs this test, so do **not** attribute it to MrBeast/Harris/etc. without a source. | Between every adjacent major beat ask: `because_of_previous?` or `complication_to_previous?`. If neither, cut, merge or justify the beat. | **PRACTITIONER.** Classic 2014 writing-room practice; old but structurally stable, not an algorithm claim. | **Parker/Stone NYU writing seminar**, transcript/video: the central section beginning with the beat-board discussion explains the rule and shows how they literally test sequences. | All lengths. Especially useful for preventing list-like middles in challenges, documentaries and skits. |
| **Three-act container** | Parker/Stone explicitly say their wall is divided into three acts. Harris explicitly says he does **not** consciously use such classical formulas. Therefore this is a valid organizational option, not a universal creator practice. | `Act A: promise + direction` → `Act B: complications/progress/reversals` → `Act C: decisive attempt + payoff + consequence` | **PRACTITIONER.** No evidence that 25/50/25 or any exact division improves YouTube retention. | The same **Parker/Stone NYU seminar** is direct evidence of an actual three-act writing-board workflow. For YouTube, MrBeast-style challenge videos can be *described* in three acts, but that post-hoc description is not evidence he outlined them that way. | Usually 8+ min; unnecessary as explicit machinery for many 60 s videos. |
| **Dan Harmon story circle / compressed hero's journey** | **Dan Harmon: verified user. YouTube adoption: not verified in this research.** Harmon’s eight beats are comfort → want → unfamiliar situation → adapt → get → pay a price → return → changed. It is a simplification of hero-journey thinking for episodic writing. | For creator video use, compress to `baseline → desire/goal → leave normal → adapt/struggle → gain → cost/reversal → return/result → change`. | **THEORY/PRACTITIONER outside YouTube.** Do not label it DATA, and do not infer intentional use merely because a challenge happens to map onto it. | No qualifying tier 1–3 evidence was found showing a major YouTuber saying “I use Harmon's circle” and then exposing the matching outline. **That absence is the finding.** | Personal quests, origin stories, travel, “I tried X for N days,” transformations; typically 8–30+ min. Poor default for tutorials/news. |
| **Compressed quest / transformation** | A more useful YouTube adaptation of hero-journey thinking: goal, obstacles, adaptation, final attempt, changed state. Unlike the full Campbell/Harmon schema, every beat maps to visible progress. | `before → goal → first attempt → obstacle → adaptation → harder attempt → outcome → after` | **PRACTITIONER synthesis**, not a measured law. | MrBeast-style challenge structures and long-form personal challenges fit this mechanically, but the agent should call it `quest` rather than asserting “hero’s journey.” | 3–30+ min challenge, fitness, learning, travel, makeover and build videos. |
| **Levels / monotonic ladder** | **1of10 publicly identifies “levels” as a recurring outlier format**, saying the format was trending and generating outliers; because the post gives the conclusion rather than a reproducible dataset, classify it as practitioner evidence. | `level_1 baseline → level_2 improvement → … → level_N extreme/best`, with each level changing at least one salient variable. | **PRACTITIONER.** | MrBeast’s **“$1 vs $500,000 Plane Ticket!”** is also an unusually clean long-form example: $1 → $1k → $10k → $25k → $100k → $300k → $500k at the timestamps above. | 30 s–15 min; particularly effective for comparison, education and spectacle where escalation is inherently legible. |
| **Question / mystery / reveal** | Curiosity-gap theory predicts motivation when people become aware of a specific gap between what they know and want to know. This does **not** prove that arbitrary “open loops” increase video retention. | `show anomaly/unknown → define exactly what is unknown → evidence/clues → eliminate possibilities → reveal → significance` | **THEORY** for curiosity mechanism; **PRACTITIONER** when implemented in creator videos. | Veritasium electricity example: problem at 0:03, explicit commitment/open loop around 0:48, then delayed model resolution. | 60 s–20 min mysteries, investigations, reveals, experiments. |
| **Kurzgesagt research-led explainer** | A canonical *production* sequence is well documented—topic/research and script first, followed by illustration, narration, animation, music/sound—but I found no official evidence that every Kurzgesagt narrative follows one fixed act template. Treat “Kurzgesagt structure” as a family, not a formula. | Recommended descriptive model: `big question/problem → simple mental model → causal explanation → expansion in scale/implications → complication/caveat → synthesis`. | **PRACTITIONER** for production process; the exact narrative beats are a synthesis, not an official Kurzgesagt rule. | Kurzgesagt’s own **“How to Make a Kurzgesagt Video in 1,200 Hours or More”** documents script-before-visual production; the process itself is the useful evidence for an agent: lock explanatory logic before expensive visuals. | 5–15 min dense animated explanations. |
| **Tutorial completion loop** | No platform source prescribes a single tutorial formula. YouTube does, however, recommend introducing compelling later material earlier and measuring where viewers abandon or skip. That supports outcome-first proof and aggressive removal of unnecessary preamble, but not an exact timing rule. | `show outcome/proof → prerequisites → step 1 → visible checkpoint → step 2/error → checkpoint → finish → verify → optional next step` | **DATA** for YouTube’s retention diagnostics; **PRACTITIONER** for this tutorial template. | Use the *finished result* as an early proof, not the entire final answer as a tease. This deliberately differs from a pure “reveal” structure. | 30 s–20+ min, depending on task complexity. |

### What to encode from Table A

The agent should **not** ask “Which famous story framework can I force this idea into?” It should first determine the viewer’s contract. **[PRACTITIONER]**

`viewer_contract = {promise, desired_answer_or_outcome, stakes, visible_progress_variable, payoff}`

Then choose a structural family:

```text
if viewer wants to know WHY / WHAT HAPPENED:
    investigation
elif viewer likely believes the wrong thing:
    misconception_refutation
elif viewer wants to accomplish a task:
    tutorial_completion
elif outcome depends on succeeding under constraints:
    challenge_quest
elif appeal is magnitude/comparison:
    levels_or_comparison
elif appeal is one unknown final object/result:
    reveal
elif appeal is personal change:
    transformation
else:
    explainer_problem_solution
```

That ordering is better supported than “always use three acts” or “always use hero’s journey.” **[PRACTITIONER]** Harris’s actual workflow begins with story ideas/research and packaging promises but consciously resists a fixed classical structure.


## Section B — Beat templates by length

The following timing budgets are **agent defaults, not algorithm benchmarks**. **[PRACTITIONER]** They synthesize three reasonably strong observations: YouTube treats the first 30 seconds as a meaningful intro region and says it should match packaging; Johnny Harris aims to reinforce his packaging promise within roughly the first minute; and MrBeast’s internal process gives the opening minute unusually high importance and then changes structural responsibilities over later portions. None of those sources proves that every creator should use the same second marks.

### Beat budget

| Length | Time budget | Beat | Open loops |
|---|---:|---|---|
| **60 s** | 0:00–0:03 | **Promise/anomaly/result glimpse.** Viewer should immediately be able to infer what kind of payoff is coming. **[PRACTITIONER]** | Open **one primary loop**. |
| | 0:03–0:08 | Define goal/question/stakes with minimum context. | Primary loop remains. Do not introduce three unanswered concepts. |
| | 0:08–0:20 | First causal step/test/evidence. Something must change. | Primary + at most one local loop. |
| | 0:20–0:35 | Complication, counterexample, stronger level or failed attempt. | Resolve local loop before replacing it. |
| | 0:35–0:49 | Decisive test / strongest evidence / level N−1. | Main loop approaching closure. |
| | 0:49–0:57 | Main payoff/result/reveal. | Close primary. |
| | 0:57–1:00 | Consequence, punchline, compressed CTA, or simply end. | Prefer zero unresolved story loops. |
| **3 min** | 0:00–0:05 | Cold-open promise, strongest anomaly, finished outcome or stakes. | Primary loop. |
| | 0:05–0:20 | Define exactly what is being solved/tested and why it matters. | Primary only unless a nested question is necessary. |
| | 0:20–0:55 | First evidence/attempt/level. | Primary + one local. |
| | 0:55–1:15 | First **mini-payoff** and turn. | Close local; main remains. |
| | 1:15–1:55 | Escalation, complication, second test or counterargument. | Main + one new local. |
| | 1:55–2:30 | Hardest/most revealing beat. | Start collapsing loops. |
| | 2:30–2:50 | Main answer/result. | Close primary. |
| | 2:50–3:00 | Meaning, before/after, next implication or end. | Zero story debt. |
| **10 min** | 0:00–0:15 | Packaging confirmation + compelling visual/proof/question. **[DATA]** This sits safely inside YouTube’s 30-second intro diagnostic; exact 15 s is a synthesis, not YouTube policy. | Primary. |
| | 0:15–0:45 | Minimal setup: goal, rules, what success/failure means. | Primary + optional stakes loop. |
| | 0:45–2:00 | First substantive attempt/evidence block. | Maximum practical default: primary + one nested. |
| | 2:00–3:15 | First payoff/answer fragment; complication changes direction. | Close nested → open replacement. |
| | 3:15–5:00 | Escalation or deeper explanatory layer. | Primary + one local. |
| | 5:00–6:30 | Midpoint result/reversal: viewer gets something substantial, not merely another tease. | Close one; optionally redefine main. |
| | 6:30–8:15 | Hardest test / decisive evidence / highest meaningful level. | Reduce loop count toward one. |
| | 8:15–9:30 | Main payoff. | Close primary. |
| | 9:30–10:00 | Consequence, reflection or next action. End once value is exhausted. | Zero. |
| **20+ min** | 0:00–0:30 | Packaging confirmation, stakes and evidence that the promised journey genuinely exists. **[DATA/PRACTITIONER]** YouTube’s first-30-second report is measured; exact creative content is practitioner synthesis. | One main loop. |
| | 0:30–1:30 | Rules/world/question; enough orientation to make future events legible. | Main + ≤1 nested. |
| | 1:30–4:00 | First complete chapter with its **own payoff**. Do not make 20 minutes one enormous tease. | Main + chapter loop. |
| | 4:00–7:00 | New constraint / broader evidence / harder attempt. | Main + chapter loop. |
| | 7:00–12:00 | Midpoint payoff or genuine reversal that changes the viewer’s model of the problem. | Main may be redefined; close obsolete loops. |
| | 12:00–18:00 | Deepest complication, character cost, strongest counterevidence or hardest stage. | Usually main + one immediate local loop. |
| | 18:00–final 10–20% | Decisive action/evidence → main payoff. | Collapse to main, then zero. |
| | final 5–10% | Consequence/meaning/denouement. | Do not reopen a giant unresolved question unless it genuinely hands into another episode. |

**[PRACTITIONER]** For a 20–40 minute video, “more duration” should generally mean **more completed chapters**, not simply more simultaneously open loops. Neither YouTube nor the creator evidence reviewed here establishes that accumulating unresolved questions increases retention. Harris’s videos can run anywhere from roughly 20 to 40 minutes because the story determines length rather than an imposed format.

**[PRACTITIONER]** MrBeast’s reported ~3-minute and ~6-minute re-engagement points are useful as a *house-style diagnostic*, not a universal interval. They are better translated into an agent check such as: “Has the state materially changed since the last major beat?” rather than “insert a pattern interrupt every three minutes.”

### Open-loop policy for the agent

Use **loop depth**, not arbitrary “re-hooks”:

```text
primary_loop:
    the packaging question / result

chapter_loop:
    the immediate obstacle or sub-question

micro_loop:
    a sentence-level unresolved item, used sparingly
```

**[THEORY]** Loewenstein’s information-gap model supports making a *specific missing piece* salient: curiosity arises when attention is focused on a gap between what is known and what one wants to know. Later work replicating related trivia paradigms finds curiosity can peak at intermediate confidence—people need enough knowledge to perceive a meaningful gap. This supports **specificity**, not endless teasing.

An appropriate default is therefore:

- **60 s:** one primary loop; usually no more than one temporary nested loop. **[PRACTITIONER]**
- **3 min:** one primary + one chapter/local loop at a time. **[PRACTITIONER]**
- **10 min:** one primary + one or occasionally two nested loops, with regular closure. **[PRACTITIONER]**
- **20+ min:** one persistent macro-question plus chapter loops that are repeatedly opened **and paid off**. **[PRACTITIONER]**

Do **not** implement “N open loops per minute.” No high-quality source in this research supports such a formula.

### Structure when there is no face or no narration

The critical distinction is that **story information does not have to be verbal**. A beat only needs to make a change legible. **[PRACTITIONER]** Johnny Harris’s process is explicitly audiovisual: while writing he simultaneously directs visuals, and his “shame cut” puts the full voice track against crude visual placeholders so his team can judge flow and length before expensive polish. Kurzgesagt likewise commits heavily to script/visual planning before final animation.

| Mode | What carries the structure | Recommended beat grammar | Evidence |
|---|---|---|---|
| **Music-only vlog / walk / hike** | Location change, clock/time, weather, distance, repeated landmarks, preparation → journey → destination, music sections and visual motifs. | `destination/goal cue → departure → progress markers → complication/change → approach → destination/payoff → quiet aftermath` | **PRACTITIONER.** No tier 1–3 retention experiment comparing narrated vs silent vlog structures was found; do not hard-code a “silent retention” cadence. |
| **Text-on-footage** | On-screen text supplies causal links that a voice-over normally would; footage proves each claim. | `text promise → visual evidence → short explanatory text → changed state → next question → visual payoff` | **PRACTITIONER.** Keep text structural rather than duplicating everything visible. |
| **Screencast** | Cursor movement, interface state, before/after, progress indicator, errors and successful result. | `show finished result → current state → action → visible checkpoint → error/constraint → fix → verified result` | **PRACTITIONER.** Outcome-first design is consistent with YouTube’s advice to introduce compelling later material earlier, but exact timing is not platform-prescribed. |
| **Faceless visual explainer** | Maps, diagrams, photos, documents, archival footage, animated annotations. | `question → evidence object → relationship → counterevidence → synthesis → answer` | **PRACTITIONER.** Harris’s own scripts include a visual-direction column; his team builds crude visual versions before fine edit. |
| **Animation** | Character goals, spatial relations, visual cause/effect, transformation, scale and motion. | `rule/world → perturbation → consequence → escalation → changed model/world → resolution` | **PRACTITIONER.** Kurzgesagt’s documented workflow places substantial script/research work before illustration and animation. |
| **No narration + no face** | Must make `goal`, `progress`, `setback` and `result` visually inferable. | Add a visible progress variable: distance, number built, object state, light, timer, route, score, before/after, completion percentage. | **PRACTITIONER.** This is an operational design rule; no platform experiment establishes one optimum implementation. |

The key agent check should therefore be:

```text
For every silent beat:
    Can a viewer with audio muted answer:
    1. What is happening now?
    2. What changed from the previous beat?
    3. What am I waiting to see next?
```

**[PRACTITIONER]** If all three answers are unclear, narration is not necessarily the solution; the underlying progression may simply be visually illegible.


## Table C — Taxonomy verdicts

The largest structural problem with the current taxonomy is that it mixes four different layers:

**story engine** = what creates progression;
**content/container format** = what kind of episode this is;
**delivery mode** = how the creator speaks/behaves;
**visual/editing grammar** = how footage is presented.

That separation matters to an agent because `challenge + faceless_animation`, `tutorial + car_yap`, `case_study + screencast`, and `personal_learning_epiphany + vlog_reflective` are all legitimate combinations. Treating “POV,” “hero’s journey,” “interview clips” and “tutorial” as equivalent taxonomy nodes prevents useful composition. **[PRACTITIONER]** Harris’s workflow is a concrete example of this separation: one story may combine field experience, later word-for-word voice-over, graphics, maps and talking-head footage while retaining one narrative promise.

### Storytelling formats

| Current item | Verdict | Recommended ontology | Why | Evidence |
|---|---|---|---|---|
| `a_vs_b_comparison` | **KEEP** | Story/container format | Comparison supplies an inherent progress variable: dimension A, B, C → verdict. | **PRACTITIONER.** The MrBeast price-ladder example shows comparison plus escalation clearly. |
| `about_me_origin_story` | **KEEP, rename slightly** | `origin_story` | Distinct arc: before → catalyst → struggle/decision → present identity. “About me” makes it unnecessarily creator-specific. | **PRACTITIONER.** |
| `breakdown_explainer` | **KEEP** | Informational structure | Useful umbrella for “how/why this works” where no misconception or task completion is necessary. | **PRACTITIONER.** Harris and Veritasium both create explainers but with different internal engines. |
| `case_study` | **KEEP** | Evidence-led structure | Concrete case → mechanism → result → lesson. Distinct from generic explainer because one entity/event supplies the spine. | **PRACTITIONER.** |
| `challenge` | **KEEP; make core** | Story engine | Goal + rules + uncertainty + obstacles + measurable result produces natural stakes/progression. | **PRACTITIONER.** MrBeast’s production model is heavily built around legible challenge/escalation. |
| `common_trap_mistake` | **RENAME** | `mistake_debunk` | “Common trap” is generally a hook framing; the underlying structure is belief/behavior → failure → correction → improved model. | **DATA for adjacent misconception mechanism; PRACTITIONER for format.** |
| `contrast` | **MERGE/SPLIT** | Merge generic contrast into `a_vs_b_comparison`; add specific `before_after_transformation`. | “Contrast” alone describes a rhetorical device, not enough of a beat sequence. | **PRACTITIONER.** |
| `day_in_the_life` | **KEEP** | Chronological observational format | Time itself supplies sequence; agent still needs a micro-goal, unusual constraint, or evolving state to avoid “and then” chronology. | **PRACTITIONER.** Parker/Stone’s criticism of “and then” is especially relevant here. |
| `episodic_series_social_show` | **MOVE** | Series/distribution wrapper | “Episodic” describes packaging across uploads, not the story engine inside an episode. | **PRACTITIONER taxonomy decision.** |
| `heros_journey` | **MOVE** | Narrative-framework layer | It is a model that can sit under an origin/quest/challenge, not a peer of “Q&A” or “tutorial.” Direct major-YouTuber adoption evidence was not found. | **THEORY.** |
| `interview_clips` | **MOVE** | Source/editing format | A clip can be a case study, Q&A, story, argument or list. “Interview” describes source material, not narrative logic. | **PRACTITIONER.** |
| `levels` | **KEEP; make core** | Escalation structure | Each stage has a natural expectation that the next changes magnitude/quality/difficulty. | **PRACTITIONER.** 1of10 explicitly calls the levels format an outlier-producing trend, though without publicly shown sample data. |
| `listicle` | **KEEP** | Modular structure | Each item is independently valuable; unlike ranking, order need not be intrinsically meaningful. | **PRACTITIONER.** |
| `personal_learning_epiphany` | **KEEP** | Personal transformation/argument | Distinct engine: old belief → experience/evidence → conflict → new belief → implication. | **PRACTITIONER.** |
| `personal_update` | **KEEP, but flag weak structure** | Update container | It has no inherent tension. Agent should require `what changed?`, `why now?`, `decision/conflict?`, `what happens next?` | **PRACTITIONER.** |
| `pov` | **MOVE/SPLIT** | Visual perspective **or** fictional `pov_scenario` | Camera POV is an editing grammar; “POV: you…” as a premise can be a skit/story format. Do not conflate them. | **PRACTITIONER taxonomy decision.** |
| `problem_solution` | **KEEP** | Core informational structure | Problem → why current approach fails → intervention → proof/limitations. | **PRACTITIONER.** |
| `q_and_a` | **KEEP as container, not story engine** | Response format | Question ordering—not act structure—determines progression. For retention, rank/order by stakes or dependency instead of chronology. | **PRACTITIONER.** |
| `ranking_rating_tier_list` | **KEEP** | Ordered comparison | Order itself creates a predicted endpoint and repeated mini-payoffs. Distinct from unordered listicle. | **PRACTITIONER.** |
| `reaction` | **KEEP** | Response structure | Strong version is `stimulus → immediate reaction → interpretation/context → consequence`, not simply footage + facial expression. | **PRACTITIONER.** |
| `reveal` | **KEEP but split** | `single_reveal` and `progressive_reveal` | A single final reveal and repeated partial reveals have different payoff architectures. | **THEORY** for information-gap rationale; **PRACTITIONER** for format. |
| `scenario_hypothetical` | **KEEP** | Counterfactual/explanatory structure | Define altered rule → follow consequences causally → surprising implication → answer. | **PRACTITIONER.** |
| `skit_humor` | **KEEP** | Fiction/comedy container | Add internal structures such as setup → escalation → reversal/button; “skit” alone is too broad for critique. | **PRACTITIONER.** Parker/Stone’s causal beat rule is useful here. |
| `tutorial` | **KEEP; make core** | Task-completion structure | Viewer intent is success, so progress/checkpoints can carry retention without artificially withholding the answer. | **PRACTITIONER**, supported diagnostically by YouTube’s advice to bring compelling content forward. |
| `yap` | **MOVE** | Delivery mode | One-take/spontaneous talking is not a narrative structure; it can carry a reaction, rant, origin story, Q&A or analysis. | **PRACTITIONER taxonomy decision.** |

**Missing storytelling structures to add**

| Add | Why it deserves its own node | Evidence |
|---|---|---|
| `investigation_mystery` | Question → evidence → competing explanations → answer. This captures Harris-style reporting more precisely than generic `breakdown_explainer`. | **PRACTITIONER.** Harris explicitly works from reporting briefs/questions and answers packaging promises. |
| `misconception_refutation` | Belief → viewer prediction → conflict → corrected model. Strong enough experimentally to separate from generic `common_trap_mistake`. | **DATA — learning, not retention.** |
| `experiment_test` | Hypothesis/question → method → trial → result → interpretation. Viewer waits for evidence rather than merely an explanation. | **PRACTITIONER.** Fits Veritasium-style experiments and creator tests. |
| `quest_journey` | Goal → route → obstacles → adaptations → arrival/result. More operational for YouTube than full hero’s journey. | **PRACTITIONER synthesis.** |
| `transformation_before_after` | Initial state → intervention/process → setbacks → final state → comparison. “Contrast” is too broad to capture this. | **PRACTITIONER.** |
| `build_makeover` | Plan/design → build stages → problems → fix → reveal/test. Strong visible progress variable makes this distinct from abstract tutorial. | **PRACTITIONER.** |
| `competition_elimination` | Contestants/options progressively removed until one winner/result remains. It creates repeated closures plus a persistent macro-loop. | **PRACTITIONER.** MrBeast’s large competition videos use elimination as a central engine. |
| `profile_documentary` | Person/place/entity → central question → chronology/evidence → interpretation. | **PRACTITIONER.** |
| `storytime_confessional` | Outcome teaser → how I got there → decision/reversal → consequence → retrospective meaning. | **PRACTITIONER.** |

### Editing and presentation styles

Your editing taxonomy is useful, but it should be renamed **`presentation_styles`** because several nodes describe camera placement or source material rather than editing.

| Current style | Verdict | Recommended change | Reason / evidence |
|---|---|---|---|
| `car_yap` | **KEEP, rename** | `car_talking_head` | Location + delivery grammar, not story. “Yap” can remain a modifier such as `script_mode=unscripted`. **[PRACTITIONER]** |
| `office_room_yap` | **KEEP, rename** | `desk_room_talking_head` | Same reason; allows scripted, bullet-scripted or improvised variants. **[PRACTITIONER]** |
| `whiteboard` | **KEEP** | `whiteboard_explainer` | Visual state accumulates as the explanation proceeds; useful distinct production grammar. **[PRACTITIONER]** |
| `split_screen` | **KEEP** | — | Compositing grammar; can compare simultaneous subjects, show reaction + source, or speaker + evidence. **[PRACTITIONER]** |
| `full_screen_hybrid` | **RENAME** | `talking_head_broll_hybrid` | “Full screen” does not identify what alternates; explicit naming makes generation/edit instructions clearer. **[PRACTITIONER]** |
| `comparison_clone` | **KEEP** | — | Useful compositing subtype for A/B, past/future self, role-play. **[PRACTITIONER]** |
| `podcast_clips` | **KEEP, rename** | `podcast_repurpose_clip` | “Podcast” describes source. Internal story still needs a hook/context/payoff extracted from conversation. **[PRACTITIONER]** |
| `visual_greenscreen` | **KEEP** | — | Creator foreground + evidence/background. **[PRACTITIONER]** |
| `notes_article_greenscreen` | **MERGE as subtype** | `document_greenscreen` under `visual_greenscreen` | Article/tweet/note is the background asset, not a distinct narrative architecture. **[PRACTITIONER]** |
| Greenscreen `reaction` | **RENAME** | `greenscreen_reaction` | Distinguishes visual grammar from the higher-level `reaction` story format. **[PRACTITIONER]** |
| `vlog_hybrid` | **KEEP** | — | Field action + stand-up/VO/B-roll. Harris’s recent field workflow is a strong example of experiential footage later stitched with scripted VO. **[PRACTITIONER]** |
| `vlog_interactive` | **RENAME / define** | `vlog_audience_interactive` or `vlog_task_interactive` | Current label is ambiguous: viewer polls and interacting with people/world are different things. **[PRACTITIONER]** |
| `vlog_pov` | **KEEP** | — | First-person capture grammar. Separate from `pov_scenario` story premise. **[PRACTITIONER]** |
| `vlog_music` | **KEEP** | `vlog_music_only` when truly no VO | Useful because absence of speech requires visual progression to carry causality. **[PRACTITIONER]** |
| `vlog_timelapse` | **MERGE as technique/modifier** | `time_compression=timelapse` | Timelapse is an editing device that can occur in builds, travel, tutorial or reflective vlog. **[PRACTITIONER]** |
| `vlog_reflective` | **KEEP** | — | Distinct emphasis on retrospective meaning/voice-over rather than only events. **[PRACTITIONER]** |
| `man_on_street_single` | **KEEP, rename** | `street_interview_single_subject` | One subject can sustain a mini-profile or one argument. **[PRACTITIONER]** |
| `man_on_street_multiple` | **KEEP, rename** | `street_interview_montage` | Multiple responses support contrast, distribution of opinions or escalation. **[PRACTITIONER]** |
| `skit_solo` | **KEEP** | — | Production/cast subtype. Story beats still come from skit framework. **[PRACTITIONER]** |
| `skit_group` | **KEEP** | — | Same. |
| `skit_lip_sync` | **KEEP** | — | Audio-driven performance grammar rather than independent story structure. **[PRACTITIONER]** |
| `skit_transformation` | **KEEP** | — | Useful editing/performance hybrid because visible identity/state change often is the payoff. **[PRACTITIONER]** |
| `faceless_visual_explainer` | **KEEP; make core** | — | Broad VO + visuals family. Harris’s visual-direction workflow and similar documentary explainers demonstrate why narrative and presence should be separated. **[PRACTITIONER]** |
| `faceless_animation` | **KEEP** | — | Strong distinct production pipeline; Kurzgesagt documents script/research → illustration → animation. **[PRACTITIONER]** |
| `faceless_clipping` | **RENAME** | `found_footage_compilation` / `licensed_clip_explainer` | “Clipping” says little about narrative and can obscure copyright/source issues. **[PRACTITIONER]** |
| `faceless_gameplay_narration` | **KEEP** | — | Gameplay can be illustration/background while narration carries a separate story. **[PRACTITIONER]** |
| `faceless_physical_explainer` | **KEEP** | — | Hands/objects/demonstration visibly carry explanation. **[PRACTITIONER]** |
| `faceless_reaction_explainer` | **KEEP as hybrid** | — | Useful when source stimulus + commentary/evidence alternate without visible host. **[PRACTITIONER]** |
| `faceless_text_conversation` | **KEEP** | — | Text/dialogue is both narration and visual object; useful distinct short-form grammar. **[PRACTITIONER]** |
| `stop_motion` | **KEEP** | Move under `animation_technique` | It is a production technique compatible with tutorials, skits, explainers, builds, etc. **[PRACTITIONER]** |

**Missing presentation styles worth adding**

| Add | Why |
|---|---|
| `screencast` | Essential for software, research, coding and workflow videos; cursor/interface state becomes the progress variable. **[PRACTITIONER]** |
| `screencast_talking_head_pip` | Common hybrid distinct from pure screencast. **[PRACTITIONER]** |
| `documentary_archival` | Archive/documents/maps/interviews/VO, distinct from generic B-roll. Harris-style visual reporting belongs partly here. **[PRACTITIONER]** |
| `overhead_hands` | Cooking, drawing, repair, unboxing, physical tutorials and craft. **[PRACTITIONER]** |
| `kinetic_typography` | Text itself is primary visual movement/story carrier. **[PRACTITIONER]** |
| `slides_motion_graphics` | Important solo-creator low-cost explainer mode between static slides and full animation. **[PRACTITIONER]** |
| `screen_plus_document_camera` | Useful technical/tutorial hybrid where digital and physical actions alternate. **[PRACTITIONER]** |

### How analyst taxonomies differ from yours

**1of10 is fundamentally an *outlier/idea-format* system, not a comprehensive narrative ontology.** Its public material emphasizes identifying current outlier videos, selecting reusable idea formats, then breaking down why a chosen format/video performed. Its own public post specifically calls out `levels` as a format producing outliers. That means 1of10’s unit of analysis is closer to **repeatable packaging/content format** than to your combined story/editing taxonomy. **[PRACTITIONER]**

**Sandcastles is also primarily an outlier/research workflow.** Its public product describes a cross-platform feed across Instagram, TikTok and YouTube Shorts for finding outlier videos; a September 2026 Creator Science interview describes watchlists, outlier scores, deep video analysis and Claude/MCP-assisted workflows. Self-reported reach and hit-rate claims are practitioner claims, not independently shown experimental data. **[PRACTITIONER]**

Kallaway publicly markets instruction around **ideas/formats → hooks/storytelling → recording/editing**, which is actually a useful confirmation that these should be separate layers in your system. His current material says the script coach compares a user’s scripts with winning examples and separately teaches visual layouts/recording. **[PRACTITIONER]**

A surfaced Kallaway post advertises “top 6 storytelling formats,” but the accessible public result did **not** expose a reliable list of all six. I would therefore **not** manufacture a “Kallaway six-format taxonomy” from reposts or course summaries. **[PRACTITIONER / negative finding]**

Likewise, **Hook Genius** appears publicly as a hook/script diagnostic or report in Kallaway’s ecosystem rather than a stable, published, academically inspectable storytelling taxonomy. It is better understood as tooling around openings than as an alternative to your format ontology. **[PRACTITIONER]**

The recommended final schema is therefore:

```yaml
video:
  story_engine:
    - investigation
    - challenge
    - tutorial
    - misconception_refutation
    - comparison
    - levels
    - reveal
    - transformation
    - experiment
    - quest
    - problem_solution
    - list
    - ranking
    - reaction
    - skit

  framework_optional:
    - but_therefore
    - three_act
    - story_circle
    - hero_journey

  container:
    - case_study
    - day_in_life
    - q_and_a
    - personal_update
    - origin_story
    - profile_documentary
    - episodic_series

  presentation:
    - talking_head
    - car_talking_head
    - greenscreen
    - screencast
    - vlog
    - street_interview
    - faceless_visual
    - animation
    - gameplay
    - overhead_hands
    - archival_documentary
    - stop_motion

  scripting_mode:
    - word_for_word
    - beat_scripted
    - semi_scripted
    - unscripted

  payoff_architecture:
    - single_final
    - progressive
    - chaptered
    - outcome_first_then_process
```


## Section D — Stakes, tension and payoff rules

### Stakes

| Rule | Evidence level | Evidence and implementation |
|---|---|---|
| **Make the stakes legible before trying to escalate them.** A viewer cannot perceive escalation if they do not know what success, failure or uncertainty means. | **PRACTITIONER** | MrBeast challenge openings tend to establish prize/rule/end-state immediately; his internal guide puts extreme weight on the opening. |
| **Money is only one stakes variable.** Use `money`, `time`, `difficulty`, `scarcity`, `physical/technical risk`, `reputation/social consequence`, `personal meaning`, or `epistemic uncertainty`. | **PRACTITIONER** | MrBeast demonstrates money/time/competition stakes; Harris frequently uses epistemic/political questions rather than prizes. |
| **Curiosity itself can be a real stake when the viewer cares about resolving a precise knowledge gap.** | **THEORY** | Loewenstein frames curiosity as deprivation created by a perceived gap in knowledge; modern replication work supports an interaction between knowledge/confidence and curiosity. This research does not measure YouTube watch time. |
| **Personal stakes require specificity.** “This mattered to me” is weaker than a visible decision, sacrifice, deadline, relationship or identity consequence. | **PRACTITIONER** | Operational storytelling rule; not causally tested in the sources reviewed. |
| **Escalation means changing the state, not merely using more excited language.** Increase difficulty, narrow options, reveal a constraint, raise cost, introduce stronger evidence, reverse a prior belief or shorten the deadline. | **PRACTITIONER** | MrBeast’s escalating price/experience ladder visibly changes the experience rather than only narrating “this is crazier.” |
| **A complication should causally affect what comes next.** | **PRACTITIONER** | Parker/Stone’s “but/therefore” test is the clearest direct articulation: merely connecting beats with “and then” creates sequence without causality. |
| **Do not prescribe a universal escalation interval.** | **PRACTITIONER** | MrBeast’s reported minute ranges are one creator organization’s practice; Harris explicitly says he does not calculate a standard formula and writes pacing intuitively. |

For agent implementation, give every major beat a state-change vector:

```text
beat.change = one_or_more_of(
    progress_up,
    progress_down,
    stakes_up,
    option_removed,
    new_constraint,
    new_evidence,
    belief_reversed,
    relationship_changed,
    time_reduced,
    uncertainty_reduced,
    uncertainty_reframed,
    mini_goal_completed
)
```

**[PRACTITIONER]** Flag two consecutive major beats whose `change` field is empty. That is a much stronger structural diagnostic than blindly demanding a cut or pattern interrupt.

### Payoffs

| Rule | Evidence level | Evidence and implementation |
|---|---|---|
| **The main payoff must answer the packaging promise.** | **PRACTITIONER** | Harris explicitly distinguishes clickable packaging from the deeper story but says the promised question must be satisfyingly answered by the end. |
| **Confirm the promise early; do not spend the opening proving that you deserve to begin.** | **DATA** | YouTube says first-30-second retention can reflect whether content matches title/thumbnail expectations and recommends experimenting with the first 30 seconds. |
| **A late “top moment” is not automatically evidence it should remain late.** | **DATA** | YouTube explicitly says that when top moments occur later, creators should consider introducing that compelling content earlier because audience size normally decreases over the video. |
| **Spikes are ambiguous.** They may mean viewers rewatched/shared a strong moment **or** that a segment was unclear and required rewatching. | **DATA** | This is YouTube’s own warning. Do not let the agent call every spike a “great payoff.” |
| **Dips are behavior, not diagnosis.** They show viewers skipped or stopped watching; the graph alone does not tell you why. | **DATA** | YouTube defines dips this way and recommends reviewing the segment to determine the cause. |
| **Use periodic mini-payoffs in longer pieces instead of one 20-minute tease.** | **PRACTITIONER** | MrBeast-style escalation repeatedly delivers new experiences before the headline maximum; the plane video gives $1k/$10k/$25k/$100k/$300k experiences before $500k. |
| **A mini-payoff should close something.** “Things get even crazier later” without resolving the present beat creates debt rather than reward. | **PRACTITIONER** | Synthesis of causal/creator practice; no platform experiment establishes a required ratio. |
| **When a payoff closes the only reason to stay, either end soon or establish the next legitimate question before/within that payoff.** | **PRACTITIONER** | This follows the structure of multi-stage challenge videos. It should not be presented as a measured universal post-payoff effect. |
| **Do not claim that retention necessarily falls after a payoff.** | **DATA — negative finding** | YouTube documents dips, spikes and gradual decline but does not publish a rule that “payoff causes drop-off.” A post-payoff cliff must be observed in the video’s actual graph. |
| **For search/tutorial intent, show proof of the answer early and reserve final verification for later.** | **PRACTITIONER** | This is more compatible with YouTube’s “move compelling material earlier” guidance than deliberately hiding useful information until the final seconds. |
| **For a reveal/challenge, the largest *irreversible* outcome often belongs late, but meaningful smaller rewards should occur earlier.** | **PRACTITIONER** | The MrBeast plane example is a clear progression from smaller experiences to headline endpoint. |
| **The biggest payoff is not necessarily the most expensive spectacle. It should resolve the strongest promise.** | **PRACTITIONER** | Harris’s work often resolves an explanatory question rather than a material prize; MrBeast’s more recent stated pivot also cautions against equating bigger budgets with automatically stronger stories. |

### “Reward schedules” and dopamine

This is one area where creator language often outruns the evidence.

**[THEORY]** Basic reward-prediction research shows dopamine neurons respond strongly when rewarding events are better than predicted and adapt when outcomes become predicted. That is legitimate neuroscience, but it is **not evidence that a YouTube editor should mimic a variable-ratio slot-machine schedule every N seconds.**

**[THEORY]** Information-gap research supports curiosity generated by missing information, and later experiments support nuanced relationships between prior knowledge and curiosity. It does **not** establish an optimal “open loop every 20 seconds.”

So the agent should replace:

> “Inject dopamine hits / rewards every 20–30 seconds.”

with:

> **[PRACTITIONER] “For every chapter, identify what concrete value the viewer receives before asking them to invest in another unresolved question.”**

That phrasing is both more defensible and more useful.


## Writing craft, outlining and pre-shoot validation

Johnny Harris provides the strongest recent, detailed creator workflow in the searched material.

**[PRACTITIONER]** In his March 2025 process interview, Harris describes an approximately four-month end-to-end cycle on some videos: he greenlights an idea with a **reporting brief**, a researcher can spend three to four weeks building a roughly **60–80-page research digest**, then Harris curates/outlines it into a story and spends roughly three to four concentrated days in “scripting week.” He says the writing process is also visual direction and art direction rather than words alone.

**[PRACTITIONER]** Harris increasingly separates **field spontaneity from explanatory precision**. He says that while traveling he has moved away from over-engineered scripted stand-ups toward reacting, experiencing and interacting with people; after returning, he writes connective/explanatory prose word-for-word and records it as voice-over. This is a strong argument for an agent supporting at least three scripting modes rather than assuming “scripted vs unscripted” is binary.

Recommended representation:

| Scripting mode | What is fixed before shooting | Best uses | Evidence |
|---|---|---|---|
| `word_for_word` | Nearly all spoken lines + visual cues | Dense explainers, narration, legal/technical accuracy, animation | **PRACTITIONER.** Harris uses word-for-word connective VO after field reporting. |
| `beat_scripted` | Hook, story beats, facts, payoff; wording flexible | Talking head, commentary, case studies | **PRACTITIONER synthesis.** |
| `semi_scripted_field` | Goal, questions, locations, constraints, must-get shots; reactions unscripted | Vlogs, travel, challenges, interviews | **PRACTITIONER.** Mirrors Harris’s shift toward experiential field work plus later scripted VO. |
| `unscripted_yap` | Topic and perhaps 2–5 anchor beats | Reactions, updates, conversational clips | **PRACTITIONER.** Agent should critique missing progression but not force literary dialogue. |
| `visual_script` | Screen state/shot/graphic paired to every beat | Faceless, animation, screencast, documentary | **PRACTITIONER.** Harris writes/visually directs concurrently; Kurzgesagt’s pipeline similarly locks substantial script work before animation. |

### The strongest pre-edit test is a low-cost story cut

**[PRACTITIONER]** Harris calls an early version a **“shame cut”**: effectively a radio/assembly edit containing the complete voice track plus crude screenshots/placeholders, music and rough visuals. It lets the team watch the story, judge flow and length, cut material, and provide feedback before fine production. That is much closer to a useful YouTube “table read” than the generic advice to simply read a script aloud.

For the solo-creator agent, implement an equivalent:

```text
PRE-SHOOT / PRE-FINE-EDIT STRUCTURE TEST

1. Read/record scratch VO.
2. Drop in still frames or text cards for every planned visual.
3. Time the entire outline.
4. Mark:
   - packaging promise confirmed?
   - first meaningful progress?
   - first payoff?
   - longest no-state-change span?
   - redundant context?
   - loop opened?
   - loop closed?
   - final promise satisfied?
5. Cut/reorder before shooting expensive coverage.
```

**[PRACTITIONER]** This is much more evidence-aligned than asking an LLM to output a fictional “predicted retention percentage.” Actual retention is viewer behavior measured after publication; YouTube’s analytics can then validate or falsify the structural hypothesis.

### Packaging should be tested before the script is locked, but should not dictate every beat

**[PRACTITIONER]** Harris says he often develops two or three possible packaging concepts while deciding whether a story has “legs”; he calls packaging a billboard and a clear promise. At the same time, he explicitly says the packaging does **not** define the entire story—it defines one promise he knows he must answer.

That suggests a highly useful agent check:

```text
TITLE/THUMBNAIL PROMISE:
"Why is X happening?"

SCRIPT:
- Does opening confirm this is genuinely the subject?
- Does middle deepen rather than replace that question?
- Does final answer it?
- Is there valuable material that does not serve it but earns inclusion
  by creating a stronger secondary question?
```

### Research and fact-checking are part of structure, not a postscript

**[PRACTITIONER]** Harris says assertions can carry multiple fact-check sources and that his team publishes source documents; he describes storytelling as curating chaotic information into a firm linear presentation. The implication is important for an AI script agent: **selection and order should happen after evidence gathering, not by generating a dramatic arc first and looking for facts to fill it.**

**[PRACTITIONER]** Kurzgesagt’s documented workflow similarly places research/script work before illustration and animation; this is especially important because visual production is expensive enough that late structural changes are costly.

### Use outlier libraries for format discovery, not as causal proof

**[PRACTITIONER]** 1of10 says it uses outlier databases to identify formats and alternative/remixed ideas, and then breaks down why selected formats/videos performed. Sandcastles similarly centers watchlists and cross-platform outlier discovery. These are valuable **idea-validation practices**, but an outlier does not isolate storytelling structure as the causal reason for performance: topic, creator, packaging, distribution and audience can all contribute.

A good agent pipeline is therefore:

```text
outlier discovery
    ↓
extract repeatable premise / format
    ↓
separate packaging from story mechanics
    ↓
identify viewer contract
    ↓
draft beat sheet
    ↓
causality test ("but / therefore?")
    ↓
payoff audit
    ↓
scratch / shame cut
    ↓
publish
    ↓
actual retention analysis
    ↓
update creator-specific priors
```

**[DATA]** The final step is where the real evidence appears: flat sections, gradual declines, spikes and dips in the creator’s own YouTube retention graph.


## Section E — Myths, failure modes and contested advice

| Advice / structure | Verdict | Why |
|---|---|---|
| **“Every YouTube video needs the hero’s journey.”** | **MYTH / overfit — THEORY** | The hero’s journey and Harmon circle are valid narrative models, but I found no strong evidence that leading YouTube creators generally outline with them. Harris explicitly rejects the idea that humans require one ultimate classical structure. |
| **“Johnny Harris uses question → journey → answer as a rigid formula.”** | **TOO STRONG — PRACTITIONER** | He unquestionably uses packaging questions/promises and answers them, but says he does not consciously follow fixed rising-action/act formulas. Encode the promise mechanism, not a fictitious Harris template. |
| **“MrBeast says every minute literally has to be bigger than the previous minute.”** | **OVER-LITERAL — PRACTITIONER** | His production philosophy strongly emphasizes escalating interest/wow factor and defined minute ranges, but it is a house method, and his later public direction has moved toward more emotional/story-led work as pure spectacle becomes less novel. |
| **“Re-hook every 20/30/60 seconds.”** | **UNSUPPORTED UNIVERSAL — PRACTITIONER** | No official platform source establishes such an interval. MrBeast has creator-specific re-engagement timing; Harris says pacing emerges intuitively and rejects a fixed universal format. |
| **“Open as many loops as possible.”** | **UNSUPPORTED — THEORY/PRACTITIONER** | Curiosity research supports salient information gaps, not accumulating unresolved narrative debt. A clear primary question plus temporary nested question is more defensible. |
| **“Open loops work because dopamine is released on a variable-ratio reward schedule.”** | **NEUROSCIENCE OVERREACH — THEORY** | Reward-prediction research is real, but it does not establish an optimal video-editing schedule. Do not turn general dopamine findings into a YouTube cadence claim. |
| **“Always hide the answer until the final seconds.”** | **FALSE AS A GENERAL RULE — DATA/PRACTITIONER** | YouTube explicitly suggests bringing compelling later material earlier. Search/tutorial viewers often benefit from result proof early; suspense videos may legitimately defer the decisive result. |
| **“Always save the biggest payoff for last.”** | **CONTEXT-DEPENDENT — PRACTITIONER** | For a single-reveal/challenge, usually sensible. For tutorials, explainers and multi-chapter documentaries, viewers need substantial intermediate value. MrBeast’s price ladder pays out at each tier before the maximum. |
| **“Retention always crashes after you reveal the answer.”** | **NOT ESTABLISHED — DATA** | YouTube documents what dips/spikes mean but does not state that payoffs universally create a drop. Check your own graph instead of baking this assumption into the script. |
| **“A retention spike means the segment was great.”** | **FALSE — DATA** | YouTube says spikes may indicate rewatching/sharing **or confusion that forces viewers to replay**. |
| **“A dip tells you exactly what was wrong.”** | **FALSE — DATA** | A dip tells you people skipped or stopped; it does not identify whether the cause was boredom, confusion, fulfilled intent, a sponsor, mismatch, etc. |
| **“There is one good retention benchmark, e.g. X% at 30 seconds.”** | **MYTH — DATA** | YouTube defines the 30-second intro metric but does not publish one universal passing grade; it provides typical-retention comparisons against recent similar-length videos. |
| **“Backstory first so viewers understand everything.”** | **USUALLY A FAILURE MODE — DATA/PRACTITIONER** | The opening must first confirm why the viewer clicked. Context that is necessary *for the next beat* is valuable; context that merely proves the creator researched the subject delays the packaging promise. YouTube explicitly ties strong intros to matching title/thumbnail expectations. |
| **“Start with ‘In this video, I’m going to…’ is always bad.”** | **MYTH IN ABSOLUTE FORM — PRACTITIONER** | The phrase itself is not the problem. A concise sentence can efficiently confirm the promise. The failure mode is redundant throat-clearing that adds no new stakes, specificity, evidence or curiosity. No platform source shows that those five words themselves reduce retention. |
| **“Never explain context in the hook.”** | **TOO ABSOLUTE — PRACTITIONER** | Context is useful when it is what makes the stakes comprehensible. Remove *unnecessary* context, not all context. |
| **“More cuts = more retention.”** | **UNSUPPORTED — PRACTITIONER** | YouTube’s analytics measure viewer behavior, not edit frequency. No credible source reviewed here establishes a causal rule that more cuts improve retention. A confusing rapid sequence can even produce rewatch spikes that YouTube warns may reflect lack of clarity. |
| **“Pattern interrupt” is a story beat.** | **CATEGORY ERROR — PRACTITIONER** | A camera angle, zoom, meme or B-roll change may refresh presentation without changing story state. The agent should distinguish `visual_change` from `narrative_change`. |
| **“If nothing dramatic happens, manufacture tension.”** | **BAD RULE — PRACTITIONER** | Nonfiction can use epistemic tension—What is true? Why did this happen? Will this method work?—rather than fake personal danger or exaggerated consequences. Harris’s reporting and Veritasium’s conceptual conflicts demonstrate high-interest structures without challenge-show stakes. |
| **“Every minute must be more extreme than the last.”** | **NOT GENERALIZABLE — PRACTITIONER** | Explanatory videos often deepen rather than enlarge: stronger evidence, a counterexample or a changed mental model can be an escalation. Harris’s rejection of fixed formulas and MrBeast’s evolving story focus both argue against literal scale inflation. |
| **“Three acts means 25% setup / 50% confrontation / 25% resolution.”** | **UNVALIDATED FOR YOUTUBE — PRACTITIONER** | Parker/Stone verify three-act organization, but not a retention-optimal YouTube ratio. Harris explicitly writes without fixed act proportions. |
| **“The script should predict an exact retention curve before shooting.”** | **FALSE PRECISION — DATA** | Real retention is produced by real viewers and appears in video-level analytics after publication. A pre-shoot agent can flag likely friction and compare against historical creator data, but it should not invent percentages. |
| **“If a format produced an outlier, the format caused the outlier.”** | **CAUSALITY ERROR — PRACTITIONER** | 1of10/Sandcastles outlier discovery is useful for finding repeatable patterns, but public outlier identification by itself does not isolate format from topic, thumbnail, creator, audience and distribution. |
| **“Editing style and story format are the same taxonomy.”** | **CATEGORY ERROR — PRACTITIONER** | A tutorial can be screencast, talking head, animation, POV or faceless physical demonstration; a challenge can be vlog, documentary or animation. Your agent should compose these dimensions rather than choose one flat label. Harris’s mixed field/VO/visual workflow is a concrete example. |

The highest-confidence script critic can therefore be surprisingly simple:

```text
STRUCTURE CRITIC

1. PROMISE
   What exactly did the packaging promise?
   Does the opening confirm it within the first meaningful beat?

2. QUESTION / GOAL
   What concrete outcome is unresolved?
   Is it specific enough that the viewer knows what resolution looks like?

3. CAUSALITY
   For every major beat:
       does it happen BECAUSE OF the previous beat
       or COMPLICATE the previous beat?
   Flag "and then" sequences.

4. PROGRESSION
   Does each major beat change:
       progress, knowledge, stakes, constraints,
       options, belief, relationship, or time?

5. STAKES
   What is gained/lost/learned?
   Are the stakes visible rather than merely asserted?

6. PAYOFF DEBT
   List every question the script opens.
   Where does each close?
   Flag loops with no meaningful resolution.

7. VALUE CADENCE
   In long videos, does each chapter deliver a result,
   discovery, laugh, transformation, useful fact,
   or completed sub-goal before asking for more attention?

8. CONTEXT
   Could any setup move later, to the first moment it becomes necessary?

9. PAYOFF
   Does the ending satisfy the title/thumbnail promise?
   Is the best material artificially buried?

10. FORMAT FIT
    challenge       -> goal / rules / obstacle / result
    tutorial        -> proof / steps / checkpoints / verified result
    investigation   -> question / evidence / competing explanations / answer
    misconception   -> belief / prediction / conflict / corrected model
    levels          -> monotonic progression / final extreme
    transformation  -> before / process / setback / after
    reveal          -> unknown / clues / reveal / significance

11. PRESENTATION
    Evaluate talking head, vlog, screencast, animation, greenscreen,
    etc. separately from narrative structure.

12. UNCERTAINTY
    Never invent a retention percentage.
    Label unmeasured recommendations PRACTITIONER or THEORY.
```

That rule set is much closer to what the evidence actually supports than a rigid “hook → three acts → re-hook every 30 seconds → hero’s journey → dopamine payoff” formula. **[DATA]** YouTube gives creators the post-publication evidence necessary to test those structural hypotheses at the exact moments where viewers stay, leave, skip and rewatch. **[PRACTITIONER]** The strongest creators studied here differ substantially in their preferred structure—MrBeast formalizes timing and escalation much more aggressively, while Harris explicitly resists formulas—so the agent should learn creator- and format-specific priors rather than treating one creator’s production system as a universal law.