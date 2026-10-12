# 08 · Hooks and the first 30 seconds, long-form and short-form

Source: ChatGPT Deep Research, downloaded by the author on 2026-10-12 (`~/Downloads/deep-research-report (5).md`). ChatGPT's inline citation markers (386 of them) did not export as links and were stripped; only the claims and the sources named in the text remain. The Opus agent run of the same prompt is `result-a.md`.

---

# Hooks and the Opening Window: An Evidence-Based System for Long-Form and Short-Form Video

## Evidence synthesis and recommended model

The strongest finding is not a particular sentence template. It is **promise continuity**: on YouTube, the title and thumbnail create an expectation, and YouTube explicitly defines the “Intro” retention metric as the percentage of viewers still watching after 30 seconds. Its own guidance says a high Intro percentage can mean that those first 30 seconds matched the expectation created by the title and thumbnail and kept viewers interested. YouTube recommends changing either the packaging or the first 30 seconds when that does not happen. **DATA.**

That interpretation is reinforced by YouTube's current native title/thumbnail A/B testing. YouTube chooses the winning variant by **watch-time share, not click-through rate**, explaining that good packaging should help viewers understand what the video is about rather than induce “wrong” clicks. It supports testing up to three title/thumbnail combinations concurrently. **DATA.**

So the useful model for your agent is:

> **Packaging makes the promise → opening confirms the promise → opening creates the next reason to stay.**

That is more defensible than “the hook's job is to create curiosity.” Curiosity is one possible mechanism. A good opening can instead work through immediate proof, a striking contradiction, a concrete goal under constraint, an unresolved reaction, diagnosis, transformation, or an experiment whose result is unknown. YouTube's documentation supports the contract part; creator practice supports the specific mechanisms. **DATA for the contract; PRACTITIONER for the mechanism library.**

Your current taxonomy has another problem: it mixes **different levels of description**. `curiosity`, `diagnosis`, `transformation`, and `reaction_promise` describe why a viewer might keep watching; `question` describes sentence form; `pov` describes framing; `visual_payoff` describes delivery modality; `list` and `numbered_series` describe progress structure; `bare_number` and `fake_label` are failure modes. That makes flat-category generation less useful than a compositional system. This is a synthesis of the practitioner and theory evidence, not a platform rule. **PRACTITIONER + THEORY, kept conceptually separate.**

A better internal representation is:

`hook = contract + retention mechanism + delivery + progress mechanism + proof/stakes`

For example:

`title/thumbnail promise + contradiction + visual proof + goal/constraint + unresolved outcome`

That lets the agent generate ten genuinely different hooks rather than ten paraphrases of “What if I told you…”.

Two important evidence limits apply throughout this report. First, **there is no credible evidence for a universal “YouTube viewer decides at exactly 3/5/8 seconds” rule**. YouTube's first explicit long-form analytics milestone is 30 seconds. Jenny Hoyos currently uses an under-three-second rule for short-form, but that is her practice, not a universal platform threshold. **DATA for YouTube's 30-second metric; PRACTITIONER for Hoyos's <3-second short-form rule.** Second, most hook taxonomies circulating among creators are practitioner abstractions rather than controlled causal tests. Even excellent creator analytics generally establish “this happened on my videos,” not “this sentence shape causes retention.”

The 2023 Jenny Hoyos interview used below is **possibly outdated for platform mechanics**, so I use it only for her writing process, examples and disclosed channel observations—not as evidence for a 2026 algorithm rule. Her newer 2026 material is used where available.

I could not validate a high-quality creator-video source corresponding unambiguously to the phrase **“Hook Genius”** in the requested sense; current public search results prominently resolve that name to an unrelated AI-music product. I therefore exclude any purported Hook Genius taxonomy rather than risk misattribution.

## Table A — Hook categories

| Category | Definition / mechanism | Long / short | Evidence level | Concrete evidence or example | Verdict on your taxonomy |
|---|---|---:|---|---|---|
| **question** | Opens an explicit question whose answer is withheld. Its actual retention mechanism is usually an information gap, experiment or contradiction—not grammatical question form itself. | Both | **THEORY** | Curiosity research supports increased motivation when information is missing and salient; Kang et al. found higher curiosity associated with reward-system activity and better memory for answers. This is not video research. | **MERGE as a form tag under `curiosity`, `test`, or `contrast`.** “Question” alone is too weak as a root category. “Do you want more views?” creates almost no gap. |
| **curiosity → open_loop / information_gap** | Viewer understands **what information is missing and why knowing it matters**. | Both | **THEORY**, with practitioner use | Narrative research distinguishes curiosity from suspense: curiosity can be generated when an outcome is revealed while causes are withheld; Kang et al. independently show motivational effects of epistemic curiosity. | **KEEP, rename `open_loop` or `information_gap`.** “Curiosity” is too broad; require a specific missing variable. |
| **contrast → contradiction / expectation_violation** | Establish a familiar belief/state, then show evidence or a claim inconsistent with it. | Both | **PRACTITIONER** | Paddy Galloway's 2026 “contradiction click” practice uses propositions such as why someone would sell a house for a dollar or work out less to gain muscle. He attributes 200M+ client views to work using the technique, but does not show a controlled category test, so this remains PRACTITIONER. | **RENAME `contradiction` / `expectation_violation`.** This is sharper than generic “contrast,” which can mean merely before/after. |
| **list** | Opens a bounded set and creates visible progress toward completion: N items, attempts, stages, places, mistakes. | Both | **PRACTITIONER** | In *Jenny Hoyos – How she averages 10 million views per video*, around **15:29**, Hoyos describes a list of three as a “mechanism”: viewers understand how progress is being tracked and what finishing means. | **KEEP, but demote to `progress_mechanism`.** “5 things…” is not intrinsically a hook; specificity and item value still have to create demand. |
| **pov → situational_immersion** | Frames the audience as participant or gives immediate subjective access to an unusual situation. | Mostly short; can work in long cold opens | **PRACTITIONER / evidence gap** | I did not locate high-quality category-level retention data showing that the text prefix “POV:” itself improves retention. | **KEEP as a delivery/framing tag, not a root mechanism.** Require an actual situation the viewer can instantly infer. |
| **visual_payoff → proof_first / payoff_first** | Opening image proves the promised object, result, environment or consequence before explanation. | Both | **PRACTITIONER** | In the Hoyos interview at about **9:49**, she explains the first frame of her $1 fast-food series: recognizable restaurant/location, the item and "$1" text appear immediately; she says she iterated these first-frame structures from performance observations. | **RENAME `proof_first` / `payoff_first`. KEEP.** “Payoff” can imply giving away the whole ending; “proof” better captures “show me this video is really about what I clicked for.” |
| **transformation** | Establishes state A and desired/unbelievable state B; the unresolved path from A→B sustains viewing. | Both | **PRACTITIONER + THEORY** | Outcome-first narrative structures can generate curiosity about preceding causes, but that result comes from narrative experiments rather than YouTube testing. | **KEEP.** Distinct from `proof_first`: transformation requires a meaningful state change, while payoff-first may simply reveal an object/result. |
| **diagnosis** | Names an observed failure/symptom, rejects the obvious explanation, and promises the actual cause/mechanism. | Strong long; also short | **PRACTITIONER** | Film Booth/Ed Lawrence's 2025 interview summary recommends starting from a strong question/problem and getting immediately into value rather than spending the opening on conventional introduction; retention dips are used to diagnose weak openings. No category A/B is shown. | **KEEP.** Particularly suitable for tutorials, critiques and creator education. The diagnosis must be specific enough to be falsifiable. |
| **named_framework → mechanism / method** | Promise result/problem first, then identify a concrete method that explains how the result will be produced. | Mostly long; short explainers too | **PRACTITIONER** | Hoyos repeatedly emphasizes a visible/story “mechanism”—for example shrinking constraints or a list that explains how the viewer will know the story is progressing. | **RENAME `mechanism_method`.** The useful part is the method, not having coined a name. Keep the framework name *after* the promise, as your definition already says. |
| **numbered_series** | “Day/Episode N of…” supplies continuity for returning viewers. | Mainly short | **PRACTITIONER / evidence gap** | No high-quality evidence found that saying the episode number itself improves retention; it is primarily context. | **MERGE into `series_context` / `progress_mechanism`.** Do not spend the opening merely identifying the episode; attach goal/tension immediately. |
| **reaction_promise** | Viewer stays to see a person's genuine response to a reveal, gift, result, prank, decision or consequence. | Both | **PRACTITIONER** | At about **16:32** in the Hoyos interview, she breaks down a Mother's Day story: her mother had never received a Mother's Day gift; she will change that using only $5; the eventual gift/reaction is foreshadowed while complications delay resolution. | **KEEP**, preferably `reaction_payoff`. The subject must matter and the reaction must be meaningfully uncertain. |
| **bare_number** | Statistic, price, quantity or percentage with no reason, mechanism or consequence attached. | Neither as standalone | **PRACTITIONER-derived failure mode** | Hoyos's effective numeric examples couple the number to a concrete object and visual situation—e.g. "$1" + recognizable food/location—rather than making the number do all the work. | **MOVE TO ANTI-PATTERNS.** Correctly marked as a trap. Numbers are evidence/specificity modifiers, not automatically hooks. |
| **fake_label** | Invented term/framework presented as novelty without distinct mechanism, evidence or behavior behind it. | Neither | **PRACTITIONER-derived failure mode** | YouTube's current spam policy also warns against repetitive or templated synthetic mass-production and maliciously misleading packaging; it does not prohibit named frameworks, but it raises the cost of empty templating/deception. | **MOVE TO ANTI-PATTERNS.** Correctly marked as a trap. A label should compress a real method, not manufacture novelty. |
| **direct_promise** | States exactly what the viewer will see/learn/get, without manufactured mystery. | Both | **DATA + PRACTITIONER** | YouTube explicitly ties strong 30-second retention to the opening matching thumbnail/title expectations; Film Booth likewise advocates getting immediately into promised value. | **ADD.** This is the biggest omission. Not every good hook needs mystery. Clarity itself can be the hook when the promised outcome is sufficiently desirable. |
| **goal_constraint_challenge** | “I must achieve X under Y limitation; here is what counts as success/failure.” Constraint creates stakes and a built-in story engine. | Both | **PRACTITIONER** | Hoyos's Mother's Day example at **16:32** couples goal (give mother a meaningful gift) with a $5 constraint; around **15:29** she similarly discusses MrBeast's shrinking-circle mechanism as a visible constraint that drives progress. | **ADD.** This is a major missing root category, especially for challenges, travel, experiments and creator projects. |
| **in_medias_res / consequence_first** | Begin at or near an unresolved consequence, then withhold enough causal history to make the viewer want to reconstruct how it happened. | Strong long; also short | **THEORY** | Hoeken & van Vliet's narrative experiments distinguish suspense (outcome postponed) from curiosity produced by revealing an outcome before the preceding events. This supports the mechanism, not YouTube-specific effectiveness. | **ADD.** This is not identical to payoff-first: the revealed moment should open a causal question rather than fully satisfy the video's promise. |
| **test / demonstration** | Introduces a proposition, object or method and an observable test whose outcome is not predetermined for the viewer. | Both | **PRACTITIONER + THEORY** | It combines the clarity of a question with a progress mechanism: what is being tested, how success is measured and why the result matters. Curiosity evidence supports wanting an unknown answer; creator practice supports explicit mechanisms. | **ADD.** Very useful for reviews, “I tried…”, science, comparisons, challenges and tool tests. |

### The taxonomy the agent should actually store

The cleanest implementation is **not** one enum containing all of the above. Based on the evidence, I would give the agent four independent fields:

| Layer | Recommended values | Why |
|---|---|---|
| **Retention mechanism** | `direct_promise`, `information_gap`, `contradiction`, `goal_constraint`, `transformation`, `diagnosis`, `reaction_payoff`, `test`, `consequence_first` | These describe the reason to continue. Curiosity/suspense research and current practitioner practice support keeping mechanisms distinct. |
| **Delivery** | `spoken`, `visual_proof`, `onscreen_text`, `POV`, usually combined | Hoyos explicitly designs the visual first and then adds concise verbal accompaniment; her 2026 checklist still emphasizes the first visual frame and muted comprehensibility. **PRACTITIONER.** |
| **Progress mechanism** | `list`, `countdown`, `attempts`, `map/journey`, `before_after`, `deadline`, `shrinking_resource`, `series` | Hoyos's “mechanism” concept is specifically about making the viewer understand progress and what completion looks like. **PRACTITIONER.** |
| **Surface form** | `question`, `declaration`, `command`, `conversation`, `cold_open` | These are stylistic wrappers, not independent evidence-backed reasons to watch. |

This also solves the “write ten hooks” problem: require the model to change the **mechanism**, not merely the wording.

## Table B — Hook formulas and iteration process

| Formula | Structure | Concrete example / source | Evidence | Overuse risk |
|---|---|---|---|---|
| **Contract confirmation → new tension** | `[confirm the exact clicked promise] → [give one piece of proof] → [introduce the next unresolved variable]` | YouTube's 30-second guidance directly associates high Intro retention with matching thumbnail/title expectations; its A/B system optimizes package variants for watch time rather than raw CTR. | **DATA** | Repeating the title word-for-word without adding proof or a new question feels redundant. |
| **Goal + constraint + stakes** | `I need to [specific goal], but I only have [time / money / attempts / resource], and [failure consequence].` | *Jenny Hoyos – How she averages 10 million views per video*, **16:32**: Mother's Day gift goal + **$5** constraint; the complication then drives the story. | **PRACTITIONER** | Synthetic “24-hour challenge” constraints that do not materially affect the story become cosmetic. |
| **You'd think X, but Y** | `[widely held expectation] → but → [credible contradiction] → [implicit/explicit why?]` | Paddy Galloway's 2026 contradiction-click examples include propositions such as working out less to gain muscle or selling a house for $1. The post reports client outcomes but does not show a controlled test. | **PRACTITIONER** | “Everything you know about X is wrong” without real contradiction has become indistinguishable from generic clickbait. |
| **Payoff → causal gap** | `[show result/consequence] → [identify surprising fact about it] → [rewind to cause]` | Narrative experiments find that revealing an outcome before preceding events can produce curiosity about how it came about. This is narrative theory, not platform data. | **THEORY** | Showing *all* of the interesting outcome can remove, rather than create, the unanswered question. |
| **Problem → rejected explanation → diagnosis → mechanism** | `If [symptom], it probably isn't [obvious cause]. It's [specific cause]. Here's the mechanism/fix.` | Film Booth's 2025 interview material emphasizes problem/question-first openings and moving into value rather than conventional introduction. | **PRACTITIONER** | “You're doing X wrong” becomes empty aggression when the alternative explanation is not demonstrated. |
| **Question → test → success criterion** | `Can [specific proposition]? I tested it using [method], and [observable criterion] decides whether it worked.` | Curiosity work supports wanting answers to salient unresolved questions; Hoyos's mechanism principle supplies an observable path toward resolution. | **THEORY + PRACTITIONER, separately** | “I tried X so you don't have to” with no meaningful uncertainty becomes a generic shell. |
| **Before → intervention → after** | `[state A] → [specific intervention/constraint] → [glimpse state B] → how?` | Outcome-first discourse can produce causal curiosity; the transformation itself must remain comprehensible. | **THEORY** | Unrealistic before/after framing becomes deceptive if the displayed result is atypical or unrelated to what the method actually achieves. |
| **List + ordering rule** | `There are [N] [specific items], but [ordering/ranking rule] means the last one is materially different.` | Hoyos at roughly **15:29** describes lists as mechanisms because the audience can perceive progression and know when the sequence is complete. | **PRACTITIONER** | “5 tips” with interchangeable items has a count but no escalating tension. |
| **Reaction setup** | `[specific person] has never seen/received/learned [thing] → I'm about to reveal it → [risk/constraint].` | Mother's Day story discussed by Hoyos at **16:32**: the mother, the gift, the $5 limit and later complication create a concrete reaction payoff. | **PRACTITIONER** | “Wait for their reaction” without enough reason to care about the person/result is withholding without value. |
| **Context → conflict → question** | `[minimal context necessary to parse scene] → [goal is obstructed] → [unresolved outcome]` | Narrative research distinguishes suspense generated by postponing an outcome from curiosity generated by withholding causal information. | **THEORY** | Too much “context” before conflict is exactly the problem this formula is supposed to prevent. |
| **What → why → how** | `[what is happening] → [why viewer should care] → [how the video will resolve/test it]` | This is best treated as an editorial clarity scaffold, not an empirically validated hook formula. YouTube's contract guidance supports “what”; creator mechanisms support “how.” | **PRACTITIONER-derived synthesis** | Produces bland textbook intros if each component becomes a separate explanatory paragraph. Compress it. |
| **Promise + stakes + why now** | `[specific payoff] → [consequence if unresolved] → [real deadline/change making this attempt relevant now]` | Goal/constraint practice supports the first two pieces; no high-quality source in this research established “why now” as an independently causal variable. | **PRACTITIONER-derived synthesis** | Fake urgency—“before it's too late”—is worse than omitting urgency entirely. |

The formulas should therefore be **generators, not scripts**. The agent should choose one because it fits the video's actual source of tension. It should not force every subject into “you'd think X, but Y.”

The most defensible iteration process comes from Jenny Hoyos. In the 2023 interview she describes studying large numbers of Shorts, maintaining a set of reference creators, producing multiple possible hooks, sketching visuals much like thumbnails, comparing what worked, and filtering ideas through hook, mechanism and rewatch potential. She also describes narrowing a larger pool of ideas—roughly 25 down to 10 with her team at that point—rather than treating the first phrasing as sacred. **PRACTITIONER; some channel analytics are discussed, but this workflow itself is not experimentally validated.**

Her strongest hook-writing lesson for an AI system is that **the first frame is part of the draft**. Around **3:16** she says she sketches visual concepts, decides what the viewer sees first, then adds concise verbal accompaniment. Around **9:49** she explains iterating first-frame structures based on performance. **PRACTITIONER.**

There is one useful piece of creator **DATA**, but it must not be generalized: Hoyos describes trimming roughly one second from the end of one Short and seeing its retention move from about **83% to 88%**, after which the video accelerated. That is a single-video observation, not proof that removing one second universally produces five retention points or that hooks need a particular length.

Her stated ~85% viewed-versus-swiped and ~95% retention figures in the same interview are likewise **channel-specific DATA**, not benchmark targets. She explicitly emphasizes studying your own channel. Do not encode “90% retention = good Short” as a universal rule.

### Prompt pattern for your agent

I did **not** find high-quality tier-1–3 evidence that any specific “viral ChatGPT hook prompt” reliably improves video performance. Most such claims are impossible to separate from prompt-marketing. The safer design is to encode the empirically/practically supported constraints rather than magical wording.

A research-consistent generation prompt would be:

```text
Generate 10 hook candidates for this video.

INPUTS
- Video premise:
- Target viewer:
- Title:
- Thumbnail concept:
- Actual evidence / footage / result available:
- Stakes or constraint:
- Ending / payoff:
- Format: long-form | short-form

RULES
1. Every hook must immediately confirm the same promise as the title + thumbnail.
2. Use at least 5 different retention mechanisms:
   direct_promise, information_gap, contradiction, goal_constraint,
   diagnosis, transformation, reaction_payoff, test, consequence_first.
3. Do not make 10 paraphrases of the same mechanism.
4. For every candidate output:
   - mechanism
   - exact first visual/frame
   - exact spoken first line
   - on-screen text, if any
   - what is already answered
   - what remains unanswered
   - stakes/constraint
   - progress mechanism
   - time until the core promise is understandable
5. The visual, spoken line and text must add information rather than
   redundantly saying the same thing.
6. Do not invent facts, stakes, deadlines, authority, results or framework names.
7. Ban empty phrases such as:
   "you won't believe", "this changes everything", "nobody talks about this",
   "the secret is", and "wait until the end" unless the script provides
   concrete evidence that makes the wording literally justified.
8. A number cannot be the hook unless the viewer immediately knows
   what the number measures and why it matters.
9. Prefer concrete nouns, visible actions and falsifiable claims.
10. Rank the candidates by:
   contract match, clarity, specificity, unresolved tension,
   visual strength, credibility, and distinctiveness.
```

Rules 1 and 6 are strongly supported by YouTube's expectation-matching guidance and misleading-clickbait policy; rules 2–5 and 8–10 are primarily practitioner-derived from Hoyos/Galloway/Film Booth, so the agent should not describe them internally as algorithm facts.

One testing caveat matters: YouTube can now run true concurrent native A/B/C tests on up to three **titles/thumbnails** and evaluates them by watch-time share, but this functionality is not available for Shorts. Therefore “test a long-form hook as a Short/community post” can be useful qualitative ideation, but it is **not an equivalent A/B test of the long-form opening**: audience, impression context and viewing commitment differ. **DATA for the feature limitation; the non-equivalence conclusion is an inference.**

## Section C — Rules for the first thirty seconds and first three seconds

### Long-form opening rules

| Window / issue | Agent rule | Evidence | Pass criterion |
|---|---|---|---|
| **Title + thumbnail → opening** | **The first 30 seconds must fulfill the *same proposition* the viewer thought they clicked.** Do not pivot to a broader adjacent topic. | **DATA.** YouTube says high Intro retention can mean the first 30 seconds matched expectations from title/thumbnail and kept viewers interested. | A reviewer can write one sentence describing the promise from the packaging and one from seconds 0–30; they mean substantially the same thing. |
| **First shot / first sentence** | Confirm the premise immediately rather than spending the first sentence on greeting, channel identity or generic background. | **PRACTITIONER.** Film Booth recommends diving into value; Hoyos designs the first visual before verbal accompaniment. | Removing the title/thumbnail, a first-time viewer can still identify what this video is about from the opening shot + sentence. |
| **How fast must the promise appear?** | Agent default: **first meaningful shot/sentence**, not “before second 5” as an alleged algorithm law. | **DATA/PRACTITIONER kept separate.** YouTube provides a 30-second Intro metric but no universal 3/5/8-second long-form threshold in the source reviewed; immediate confirmation is practitioner practice. | No expendable greeting/logo/channel intro precedes the promise. |
| **After confirmation** | Do not merely repeat the title. Add one of: concrete proof, constraint, contradiction, consequence, question or progress mechanism. | **PRACTITIONER.** Hoyos's mechanism framework and Galloway's contradiction practice. | By the end of the opening, the viewer knows both **what the video promises** and **what is still unresolved**. |
| **Visual hook** | Make the first useful frame evidence for the premise: result, object, location, unusual situation, before/after, experiment, constraint, or person whose reaction matters. | **PRACTITIONER.** Hoyos's $1-food first-frame breakdown and current first-frame checklist. | Screenshotting an early frame produces an image that plausibly belongs to the promised video, rather than generic B-roll/talking head. |
| **Spoken + visual + text** | Give the modalities different jobs. Visual proves/situates; speech supplies meaning/tension; text supplies a compact label/number/constraint where needed. | **PRACTITIONER.** Hoyos explicitly describes designing visual first and then concise verbal accompaniment. | Muting the opening preserves the basic situation; listening without reading preserves the core promise. Neither mode is required to duplicate every word. |
| **Context** | Include only context required to understand the conflict. Move optional origin story/background after the hook. | **PRACTITIONER.** Film Booth connects lengthy intros with retention problems and recommends getting to value quickly. | Every context sentence answers “what must the viewer know *before* the next conflict/action?” If not, cut/move it. |
| **Progress mechanism** | By roughly the end of the opening, make it possible to understand how the story can move forward: attempts, list, deadline, budget, route, score, transformation stages, investigation, etc. | **PRACTITIONER.** Hoyos uses “mechanism” for exactly this expectation-setting function. | Viewer can answer: “What will change between now and the ending?” |
| **First 30 s analytics** | Treat YouTube's 30-second Intro percentage as the primary diagnostic for whether the opening kept the click, but compare against your own videos of similar length rather than universal guru benchmarks. | **DATA.** YouTube lets creators compare typical retention against their ten latest similar-length videos. | Review relative to channel/content baseline; do not hard-code arbitrary “70/80/90% = good” thresholds. |
| **Dips and spikes** | A dip is a debugging signal, not proof of one cause. A spike may mean interest **or confusion/rewatching**. | **DATA.** YouTube defines dips as skipping/abandonment and notes spikes can be rewatch/share but can also indicate unclear material. | Reviewer forms a hypothesis, then checks edit/script context instead of blindly copying the spiked moment. |
| **Top moment occurs much later** | Consider moving the compelling idea/footage earlier—but preserve causality and comprehension. | **DATA.** YouTube itself recommends introducing compelling content earlier when a top moment occurs later because audiences generally shrink through playback. | Opening can preview/prove the later value without destroying the later payoff. |
| **Cold open / in medias res** | Use when the scene is comprehensible immediately and generates a causal or outcome question. | **THEORY.** Narrative studies support curiosity from outcome-before-cause structures and suspense from postponed outcomes. | The cold open creates a specific question. If it is merely chaotic unexplained footage, fail. |
| **Preview montage / “sizzle”** | **Optional, never default.** Include it only if each clip confirms the video's promise or creates a distinct unresolved question. | **Evidence gap.** I found no credible 2024–2026 Tier-1/2 controlled result establishing that preview montages universally increase retention. YouTube recommends moving compelling material earlier, but does **not** prescribe a montage. | Every preview shot earns its time. Delete the montage and compare whether clarity/tension actually falls. |
| **Restate premise at 30–60 s** | Do not mechanically restate. **Re-hook** only after context has changed: restate the goal with a stronger constraint, consequence or new question. | **PRACTITIONER-derived synthesis.** Creator mechanism practice supports renewing tension, not repeating information. | Second statement contains meaningful new information. Exact paraphrase of the opening = fail. |

The most important correction for the agent is therefore:

> **[DATA] “First 30 seconds matter” is true in a precise YouTube Analytics sense. “You must state your hook before second 5” is not supported by the official evidence reviewed.**

There is also no evidence here for a special hidden “mismatch penalty.” What YouTube actually documents is viewer behavior and testing: retention after 30 seconds is associated with expectation match, and title/thumbnail experiments are optimized for total watch time to discourage low-quality clicks. Saying “the algorithm detects promise mismatch and punishes you” would go beyond the source. **DATA.**

### Short-form hook rules

Short-form mechanics are deliberately limited here because your Task 11 covers them in depth.

| Window / issue | Agent rule | Evidence | Pass criterion |
|---|---|---|---|
| **First ~3 s** | Make the premise or compelling anomaly understandable inside the opening beat; do not rely on a setup sentence whose meaning arrives later. | **PRACTITIONER.** Jenny Hoyos's 2026 checklist explicitly uses “under three seconds” as her rule. | At 3 s, reviewer can state the situation and the unresolved reason to continue. |
| **First frame** | Start with the object/result/problem/person/constraint rather than generic movement or decorative B-roll. | **PRACTITIONER.** Hoyos describes recognizable fast-food location + object + $1 text as a first-frame construction and continues emphasizing first-frame clarity in 2026. | Frame 1 materially explains the premise. |
| **Muted comprehension** | Design the visual/text so the basic premise survives with audio unavailable; speech can add nuance and personality. | **PRACTITIONER.** Hoyos explicitly uses a mute-understanding test. Do **not** turn this into the unsupported claim that “most viewers watch muted.” | Muted first three seconds still reveal topic + important object/action. |
| **Visual complexity** | Prefer a dominant subject and few competing objects in the opening. Hoyos's current personal checklist says no more than roughly three salient objects. | **PRACTITIONER**, not general data. | Reviewer identifies the focal subject instantly; if multiple items compete, simplify. |
| **Hook–body–close** | Treat the opening as a distinct attention phase, but do not mistake TikTok ad guidance for organic-ranking science. | **PRACTITIONER/platform creative guidance.** TikTok's official Creative Codes describes a Hook–Body–Close structure and suggests suspense, surprise or emotion as hook techniques; this is advertising guidance, not an organic-feed experiment. | Useful as creative vocabulary, never cited by the agent as proof of an organic algorithm preference. |
| **Foreshadow payoff** | Give evidence that the promised ending/result genuinely exists without necessarily revealing all of it. | **PRACTITIONER.** Hoyos's 2026 checklist includes foreshadowing the ending inside the hook. | Viewer sees enough proof to trust the promise but retains an unresolved causal/outcome question. |

Psychology supports one narrow part of this, not the three-second timing: visually salient new onsets can attract attention under laboratory conditions, but the attentional-capture literature is contested and newer reviews describe a more conditional picture. Therefore “make something move/change every second” cannot be inferred from attention research. **THEORY.**

The agent should distinguish **attention capture from retention**. A flash, cut, zoom or sudden object can win milliseconds of orientation without giving the viewer a reason to continue. There is no basis here for treating faster editing as a substitute for premise clarity. **THEORY.**

## Section D — Hook critique checklist

Run this checklist **in order**. A later strength should not rescue an earlier fatal failure; in particular, curiosity cannot compensate for a broken title/thumbnail contract.

| Order | Reviewer check | Evidence | PASS | FAIL |
|---|---|---|---|---|
| **Contract identity** | Does the opening deliver the proposition made by title + thumbnail? | **DATA.** YouTube explicitly links high 30-second Intro retention with expectation match. | Same object/outcome/problem is unmistakably present. | Opening pivots, delays the real subject, or quietly weakens the promise. |
| **Truth / deliverability** | Can the script genuinely deliver every opening claim, image and implied result? | **DATA / policy.** YouTube prohibits maliciously misleading titles, thumbnails/descriptions or imagery used to trick viewers into content that does not deliver the promise. | Claim is supported by actual footage/evidence/ending. | Outcome, authority, deadline, reaction or result is invented/exaggerated beyond what the video shows. |
| **Immediate comprehension** | Can a new viewer explain what is happening without channel lore? | **PRACTITIONER.** Hoyos emphasizes simple, readable, highly visual openings. | One clean sentence describes the situation. | Requires several setup sentences before the viewer knows why they are watching. |
| **Concrete first frame** | Does the visual prove/situate the promise? | **PRACTITIONER.** Hoyos first-frame process. | Relevant person/object/result/location/constraint visible. | Decorative B-roll, logo, generic face shot, empty establishing shot. |
| **Retention mechanism** | Why exactly should the viewer watch the next beat? | **PRACTITIONER + THEORY separately.** Contradiction, mechanism and narrative curiosity provide defensible options. | Reviewer can name the unanswered variable: outcome, cause, reaction, test, transformation, etc. | Only “interesting tone,” vague hype or an adjective such as “crazy.” |
| **Specificity** | Does the hook contain concrete nouns/actions/constraints rather than abstractions? | **PRACTITIONER.** Hoyos's working examples couple numbers to visible objects and goals. | “$5 gift for my mom,” “$1 burrito,” observable test/result. | “A crazy secret changed everything.” |
| **Stakes / value** | Is there a reason the unresolved question matters? | **PRACTITIONER.** Goal/constraint and reaction examples supply consequence/value, while contradiction works only when the underlying assumption matters to the audience. | Losing, wasting money/time, meaningful transformation, useful answer, social reaction, etc. | Curiosity gap resolves to trivia the viewer has no reason to care about. |
| **Progress mechanism** | Can the viewer understand how the video will move toward resolution? | **PRACTITIONER.** Hoyos's “mechanism” principle. | Attempts, stages, deadline, list, map, experiment, budget, score, investigation. | Infinite talking with no visible route toward payoff. |
| **Modality division** | Do speech, image and text complement instead of merely duplicating each other? | **PRACTITIONER.** Hoyos sketches the visual first and adds concise verbal accompaniment. | Each mode contributes information. | Voice reads every word already occupying the screen while visual adds nothing. |
| **Compression** | Can anything before the first real value/tension be deleted? | **PRACTITIONER.** Film Booth advises getting immediately into value; YouTube recommends modifying first 30s when Intro retention is weak. | No greeting, bumper, self-introduction or generic setup is required before premise. | Hook starts after “Hey guys, welcome back…” or equivalent removable material. |
| **Novelty without falsity** | Is the surprising piece genuinely specific rather than rhetorical contradiction? | **PRACTITIONER.** Galloway's contradiction concept requires a belief worth resolving; YouTube prohibits maliciously deceptive packaging. | Surprising claim is demonstrable later. | “Everything you know is wrong” followed by ordinary advice. |
| **Category independence** | Is this candidate actually different from the other candidates? | **PRACTITIONER-derived synthesis.** Hoyos generates/filters multiple ideas and hook shapes rather than only phrasing one idea repeatedly. | Different mechanism: e.g. direct proof vs contradiction vs test. | Ten variants differ mainly in adjectives/synonyms. |
| **Analytics plan** | After publication, is there a measurable hypothesis to inspect? | **DATA.** YouTube supplies Intro %, detailed starts/stops, dips, spikes and typical-retention comparisons. | “If contract is unclear, expect excess early loss relative to similar videos; inspect exact dip.” | “Hook bad because retention low” with no competing hypotheses or channel baseline. |

For machine use, I would make the first two checks **hard gates**:

```text
if not contract_match:
    FAIL
if not truthful_and_deliverable:
    FAIL
```

Then score the rest. That prevents the common failure where an LLM writes a technically exciting hook for a different video.

A useful score after the gates is:

`clarity + specificity + tension + visual_proof + stakes + progress - setup_cost - hype_debt`

“Hype debt” is a useful internal concept rather than an empirical metric: every claim the opening makes creates an obligation the eventual video must repay. The basis for treating this obligation seriously is YouTube's explicit expectation-match guidance and anti-misleading policy. **DATA basis; scoring model is synthesis.**

## Section E — Anti-patterns, myths and advice to downgrade

| Anti-pattern / alleged rule | Verdict | Evidence |
|---|---|---|
| **“CTR is the goal, so make the title/thumbnail as clickable as possible and worry about the opening later.”** | **REJECT.** YouTube's native A/B/C system explicitly chooses title/thumbnail winners by **watch-time share rather than CTR**, explaining that packaging should help viewers understand the content and avoid wrong clicks. **DATA.** |
| **Thumbnail/title promises X; opening talks about Y before eventually arriving at X.** | **FAIL.** YouTube explicitly associates strong Intro retention with the first 30 seconds matching packaging expectations. **DATA.** |
| **“The algorithm penalizes mismatch with a special mismatch score.”** | **MYTH / unsupported.** The reviewed official material documents retention, expectation matching, watch-time-based packaging tests and deceptive-content policy. It does not document a separate “mismatch score.” |
| **“The first three seconds is a universal platform law.”** | **DOWNGRADE.** Hoyos uses an under-three-second short-form rule in her own 2026 practice, and TikTok has hook-oriented ad guidance, but neither proves a universal organic threshold. YouTube's explicit long-form Intro metric is 30 seconds. **PRACTITIONER versus DATA.** |
| **“90% retention / 85% viewed is the benchmark every Short needs.”** | **REJECT as universal benchmark.** Hoyos disclosed roughly channel-level figures in 2023 but also emphasized studying your own channel; the figures are creator-specific observations. **DATA, narrowly scoped.** |
| **Bare number: “97% of creators do this wrong.”** | **TRAP unless the number immediately attaches to a mechanism and credible source.** Effective numeric openings in Hoyos's examples bind the number to a recognizable object/situation; a naked statistic supplies specificity but not automatically tension. **PRACTITIONER.** |
| **Fake named method: “The 4D Retention Matrix changed my channel.”** | **TRAP unless the framework describes a genuinely distinct mechanism.** Naming is not evidence. YouTube's present policy also explicitly targets repetitive templated/synthetic mass production and malicious deception, making generic AI-generated novelty particularly poor practice. **DATA for policy; PRACTITIONER-derived hook judgment.** |
| **“Ask a question—questions hook people.”** | **TOO BROAD.** Curiosity research supports meaningful information gaps, not arbitrary question punctuation. A viewer must care about the missing answer. **THEORY.** |
| **“Create curiosity by withholding everything.”** | **REJECT.** Effective information gaps require enough information for the viewer to know what is unknown. Narrative research distinguishes structured curiosity/suspense from mere confusion; YouTube's expectation-match evidence favors clarity about what video was clicked. **THEORY + DATA separately.** |
| **“Show the full payoff immediately.”** | **CONTESTED / conditional.** Proof-first can establish credibility, while narrative theory indicates an outcome can create curiosity about its causes. But if the result answers every relevant question, it may eliminate the reason to stay. **THEORY + PRACTITIONER.** |
| **“Always put a cinematic preview montage before the video.”** | **NO SUPPORT FOR A BLANKET RULE.** I found no Tier-1/2 2024–2026 controlled evidence showing universal benefit. YouTube advises moving compelling later material earlier, which is not the same as recommending a montage. **DATA on the narrower claim.** |
| **“Never use a preview montage.”** | **ALSO TOO STRONG.** Outcome-before-cause can theoretically generate curiosity, and a preview can function as immediate proof. The correct test is whether it confirms the contract and opens rather than closes questions. **THEORY/PRACTITIONER.** |
| **Rapid cuts / zooms / captions automatically equal retention.** | **MYTH.** Laboratory work shows salient visual onsets can capture attention, but attentional capture itself is theoretically contested/conditional and is not equivalent to sustained video viewing. **THEORY.** |
| **“Wait until the end.”** | **Usually fail unless the ending is already concretely motivated.** It states a demand rather than creating a reason. Reaction/payoff stories work when the person, goal and constraint have already made the outcome matter. **PRACTITIONER.** |
| **Episode label first: “Day 37 of…”** | **Not a hook by itself.** It may help returning viewers orient themselves but provides no independent stakes to newcomers. No strong category-level data was found. Put tension/goal in the same beat. |
| **“POV:” automatically creates immersion.** | **MYTH / no qualifying evidence found.** `POV` is best stored as a framing device. The actual hook still needs conflict, novelty, payoff, transformation, etc. |
| **Testing a hook as a Short proves the opening will work in the long-form upload.** | **REJECT as an equivalence claim.** YouTube does not offer its native A/B title/thumbnail tests for Shorts, and a Short is consumed in a different impression/viewing context. Using it as ideation is reasonable; treating results as a controlled long-form hook test is not. **DATA for test availability; inference for non-equivalence.** |
| **“One perfect hook formula works in every niche.”** | **REJECT.** YouTube tells creators to compare retention with their own similar-length videos and to experiment with different intro styles. Practitioner examples likewise use different mechanisms for food, gift/reaction, lists and challenges. **DATA + PRACTITIONER separately.** |
| **Mass-generate formulaic AI hooks and choose the most sensational.** | **BAD AGENT DESIGN and potentially adjacent to current platform anti-spam concerns when expanded into repetitive content.** YouTube's present spam policy explicitly includes automated/synthetic mass-production of highly similar content with minimal changes. The policy does not ban using AI to draft hooks; it specifically distinguishes ordinary experimentation from flooding the service with repetitive output. **DATA / current policy.** |
| **Every hook needs curiosity.** | **FALSE as taxonomy design.** YouTube's strongest official requirement is expectation fulfillment; direct value/proof can satisfy that without withholding. Curiosity is one psychologically supported mechanism among several. **DATA + THEORY separately.** |

I found **no credible 2025–2026 dataset demonstrating that a specific phrase such as “POV,” “nobody talks about this,” “here's the secret,” or “I tried X so you don't have to” has objectively become algorithmically penalized because viewers are “hook fatigued.”** The evidence supports a narrower conclusion: empty, repetitive and misleading templates are bad because they reduce specificity/contract fulfillment and, at the extreme, overlap with YouTube's current prohibitions on malicious clickbait and repetitive synthetic mass-production. Do not teach the agent invented “2026 algorithm blacklist” rules.

Likewise, I found **no documented public retraction from the named creators/analysts establishing that one previously recommended hook category has now been abandoned**. The more defensible changes are self-qualification rather than retraction. Hoyos, for example, gives channel-specific retention/viewed figures but also says creators should study their own channel; her readability heuristic is presented as a practical simplification rather than an algorithm requirement. **PRACTITIONER / creator DATA, scoped to her own material.**

The resulting agent rule set should therefore be deliberately conservative:

> **[DATA] Protect the title–thumbnail–opening contract.**
> **[PRACTITIONER] Confirm it visually and verbally as early as the format allows, then create a concrete unresolved reason to continue.**
> **[THEORY] Information gaps, suspense and outcome-before-cause structures can motivate attention to unresolved information, but psychology does not tell you a universal YouTube timestamp or retention percentage.**
> **[DATA] Diagnose the published result from your own retention graph and comparable videos rather than universal guru benchmarks.**

For the agent itself, the highest-value architectural change is to stop asking **“Which hook category is this?”** and instead ask:

**What promise was made? What mechanism creates continued demand? What does the first frame prove? What remains unresolved? What makes that unresolved thing matter? How will the viewer perceive progress toward its resolution?**

That formulation preserves the strongest parts of your taxonomy, removes the category traps, and matches the distinction the evidence supports between **click promise, immediate proof, retention mechanism and story mechanism**.