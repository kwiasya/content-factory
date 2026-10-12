# 08 Hooks: rules

A = result-a.md, C = chatgpt.md. T1 = platform page, no data shown.

## Rules

|id|rule|applies to|tag|source|confidence|
|---|---|---|---|---|---|
|R08-01|Make the opening deliver the title and thumbnail promise, and judge packages by watch time, not clicks.|both|PRACTITIONER|https://support.google.com/youtube/answer/16559650|high|
|R08-02|Say what the video is about in the first sentence; hold back only the outcome.|both|PRACTITIONER|https://www.youtube.com/watch?v=pNIYikmYsyw&t=119s|medium|
|R08-03|Put no greeting, logo or intro before the promise.|long|PRACTITIONER|https://www.youtube.com/watch?v=w52xUmjIZPk&t=1208s|medium|
|R08-04|Make the premise clear by about 3 s; frame 1 explains it.|short|PRACTITIONER|https://www.youtube.com/watch?v=u5ZX-GhSots&t=74s|medium|
|R08-05|Point speech, frame, text and audio at one subject.|both|PRACTITIONER|https://www.youtube.com/watch?v=xnOe8aA9Pmw&t=712s|high|
|R08-06|Keep the premise clear with sound off (ads, 2016).|both|DATA|https://www.facebook.com/business/news/insights/capturing-attention-feed-video-creative|medium|
|R08-07|Open a specific gap, close every loop in the video, and never hide what the video is.|both|PRACTITIONER|https://www.youtube.com/watch?v=u5ZX-GhSots&t=504s|high|
|R08-08|Use a plain direct promise when the outcome is desirable (C only).|both|PRACTITIONER|chatgpt only|low|
|R08-09|Ask only confident second-person questions (text-headline data, conflicting).|both|DATA|https://doi.org/10.1080/21670811.2017.1279978|low|
|R08-10|Use a number only as a state change or scope tied to a visible object (text data, null).|both|DATA|https://doi.org/10.1080/21670811.2017.1279978|medium|
|R08-11|Name a method only after the promise and only if a real method exists; no wordplay, jargon or vague superlatives.|both|PRACTITIONER|https://www.youtube.com/watch?v=pNIYikmYsyw&t=242s|high|
|R08-12|Show by the end of the opening how the video progresses (list, attempts, deadline); give an episode label a tension line.|both|PRACTITIONER|https://www.youtube.com/watch?v=a7VjpIqq8Xk&t=739s|medium|
|R08-13|State who, goal, constraint and stakes in the first line.|both|PRACTITIONER|https://www.youtube.com/watch?v=Nb9cQmHFLTs&t=248s|medium|
|R08-14|After confirming the promise add new information (proof, constraint, contradiction); re-hook later with something new, not a restatement.|long|PRACTITIONER|https://www.georgeblackman.com/write-on-time/what-netflix-taught-me-about-youtube-scriptwriting|medium|
|R08-15|Write candidates on different mechanisms, not paraphrases; an LLM grade filters, a human picks.|both|THEORY|https://arxiv.org/abs/2510.22954|medium|
|R08-16|Never invent stakes, results, authority or urgency; deliver every opening claim.|both|PRACTITIONER|https://support.google.com/youtube/answer/2801973|high|
|R08-17|Judge an opening by Intro % against your last 10 similar videos, not guru benchmarks.|long|PRACTITIONER|https://support.google.com/youtube/answer/9314415|high|

## Numbers

- YouTube Intro = share watching at 30 s; videos 60 s+, 100+ views; compared with your 10 latest; no benchmark (T1).
- Native A/B: 3 packages, winner by watch-time share, not Shorts (T1).
- Long-form confirm time, none measured: ~7 s (Colin and Samir), 5-15 s (1of10, vendor), 30 s (metric), ~1 min (MrBeast doc), 1-2 min (Kallaway).
- Short-form cut-off, none measured: 1.5 s (vidIQ), 3 s (Instagram skip rate, a reporting boundary; Hoyos; TikTok 2020 ads, no base rate), 4-5 s (Kallaway).
- MrBeast doc: 21 M of 60 M (35%) left in minute 1; n=1, confounded with CTR (A only).
- Hoyos viewed-vs-swiped: ~70% average, 80%+ good, 85%+ excellent (A, no graph); her channel. Trimming 1 s: 83% to 88%, n=1 (C only).
- 1of10 (vendor, unsourced): >70% at 30 s solid, >80% exceptional, <50% at 10-15 s failing.
- Text headlines, clicks not video: question -17 pp (p=0.019), forward-reference +16, negative word +17, pronouns +25, number n.s. (Kuiken 2017); +2.3% CTR per negative word, 22,743 tests (Robertson 2023).
- Kallaway, one channel, no graph: series-branded hooks ~50% worse, borrowed opening ~60% worse; jargon hook <=100 k vs 15 M views (n=2).
- Facebook IQ 2016 (ads, old): 850+ ads, muted first 10 s vs recall r2=0.82.
- Credential within ~20 s; lock-in zone 2-4 sentences (Kallaway, vidIQ).

## Taxonomy verdicts

- question: A keep as question_you; C merge into form tag; partly agree.
- curiosity: A keep as mechanism, rename secret; C rename open_loop; agree.
- contrast: A split contrarian + before_after; C rename contradiction; agree.
- list: A merge into format_promise; C keep as progress mechanism; agree (not a root hook).
- pov: A keep as pov_identity; C keep as delivery tag; label untested; agree.
- visual_payoff: A keep (foreshadow alias); C rename proof_first; agree.
- transformation: both keep; agree.
- diagnosis: both keep; agree.
- named_framework: A keep (education only); C rename mechanism_method; agree.
- numbered_series: A merge into format_promise; C merge into series_context; agree.
- reaction_promise: A rename experiment; C keep as reaction_payoff; disagree.
- bare_number: both trap; agree.
- fake_label: both trap; agree.

Additions, A: premise_stakes; fortune_teller; format_promise; experiment; authority (modifier); pattern_interrupt, audio_recognition (layers); throat_clearing, borrowed_opening (traps).
Additions, C: direct_promise; goal_constraint_challenge; consequence_first; test.

Layers: C proposes four fields: mechanism (direct_promise, information_gap, contradiction, goal_constraint, transformation, diagnosis, reaction_payoff, test, consequence_first), delivery (spoken, visual_proof, text, POV), progress (list, attempts, before_after, series), surface form (question, declaration, command, cold_open). A does not propose this model; it adds layers (pattern_interrupt, audio_recognition), a modifier and traps. Both treat curiosity as a mechanism, not a category.

## Hook formulas

- You'd think X, but Y (A: lean-in, "but", snapback): expectation, pivot, reversal. Overuse: A business shorts; C empty "everything you know is wrong".
- Context, conflict, question: minimal context, blocked goal, open question. Overuse: too much context.
- Promise + stakes + why now: payoff, consequence, reason now. "Why now" has no source in either file; fake urgency is the risk (C).
- What, why, how: topic, why care, how resolved. No source in either file; risk bland intro.
- Goal + constraint + stakes (A: premise, prize, first rule): "I must X with only Y, else Z". Overuse: cosmetic constraint, scale copied without a real prize.
- One file only. A: four S's, six power words, "X just changed Y forever", "How to X in Y", Target+Transformation+Stakes, Stop-Stack. C: payoff to causal gap, problem to diagnosis, question to test, list + ordering rule, reaction setup.

## Critique checklist

1. Idea and angle: survives a one-sentence pitch (A).
2. HARD GATE contract: opening and package state the same promise; long within ~7 s (strictest), always before 0:30; short within 3 s.
3. HARD GATE truth: the video delivers every claim, result and deadline; no policy breach.
4. Subject in the first sentence, clear without channel lore.
5. First frame shows the relevant object, person or result, with action; not logo, greeting or generic B-roll.
6. Mechanism: name the unanswered variable; a specific gap, only the outcome held back.
7. Stakes: the unknown matters to the viewer.
8. Clarity and specificity: one reading, concrete nouns; no fake_label, no bare_number.
9. Progress: the viewer sees how the video moves to payoff.
10. Layers: one subject, each adds information, sound-off holds; text 3-5 words, 3 s+.
11. Compression: no throat-clearing (except a list-format promise), no branded intro.
12. Form: question is second-person; series label has tension; nothing borrowed.
13. Lock-in: the next 2-4 sentences confirm the promise; every loop closes.
14. Candidates use different mechanisms, not synonyms.
15. Analytics plan: a hypothesis checked against Intro % of 10 similar videos.

## Refuted and myths

- Universal 3/5/8 s decision rule: C found no evidence; A found every cut-off unmeasured.
- Hidden "mismatch score"; "high CTR, low AVD is labelled clickbait": C myth; A unconfirmed.
- Retention benchmarks (65-80% at 30 s; 90%/85% Shorts target), "3 s logo costs 8-15%", Galloway 3.3 B-view study, TikTok 63%, "YouTube value in 7 s": A unconfirmed; C rejects the Shorts target.
- "Questions hook people": C too broad; A conflicting text data.
- "Withhold everything": C reject; A cites Meta's watchbait rule.
- Preview montage always or never: C no blanket rule; A spoiler studies conflict.
- Cuts equal retention; "POV:" equals immersion: C myth.
- Phrase-level hook-fatigue blacklist: neither found data.
- "Hooks matter most" (Kallaway now B-tier), "visual 100x" (unmeasured), Upworthy gap headlines (Koechley apologised): A.
- A Short test proves the long-form opening: C rejects.
- "Hook Genius" library: A, only a report in Kallaway's tool; C excluded it.

## Disagreements

- Curiosity in every hook: A yes; C no (direct_promise). Neither tested; A better sourced.
- Question: A keep narrowed; C demote to form tag. A better evidence (text experiments).
- reaction_promise: A finds no source; C gives a named example. C slightly better.
- Layers: A aligned and guessable; C different jobs, no duplication. A better sourced; compatible (same subject, new information).
- Long-form timing: A ~7 s strictest; C no 3/5/8 s rule. Both say unmeasured; A better sourced.
- Tag of YouTube Help: C DATA; A PRACTITIONER (no data shown). A better.
- Shorts benchmark: A lists Hoyos 70/80/85%; C says channel-specific. C better.

## Gaps

- No source measures seconds-to-payoff of a thumbnail promise; one broken-promise graph, n=1.
- No video-level DATA by hook category or layer; only text headlines.
- Not first-hand: Galloway, Colin and Samir on hook types, Film Booth 2024-2026, Hoyos beyond one podcast.
- No 2024-2026 preview-montage data.
- No source for "why now", "what, why, how", write-10-pick-1, Community-post hook tests, or phrase-level spam.
- C (no Coverage section): no evidence an LLM hook prompt works; no "POV:" retention data.
