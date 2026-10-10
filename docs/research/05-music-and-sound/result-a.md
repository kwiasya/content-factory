# Music, Beat-Sync and Walk-Sound Cleanup for an Agent-Edited Instagram Reels Pipeline (Oct 2026)

> Источник: deep research, принесён пользователем 2026-10-10. Инструмент (ChatGPT / Claude) не указан, переименовать файл когда станет известно. Проверка по стабу API: см. `verification.md` рядом.

Have the agent choose the music during the edit, from Epidemic Sound. Its Creator plan costs $9.99/mo billed annually, it covers Instagram, it includes stems, and it has an official MCP server that Claude Code can call to search, download and recut tracks. Use Instagram trending audio only as an occasional manual add-on: there is no legal way for the agent to get the exact in-app track as a file, so a cut built against it is approximate at best.

## TL;DR
- **Default: choose the music in the edit.** Use Epidemic Sound (Creator $9.99/mo annual or $17.99 monthly, with stems and an MCP server). Get beats from Beat This! (MIT, pip, runs on Apple MPS) and sections from all-in-one-infer. Then place cuts on downbeats, write them to Resolve as markers and edits through the Python API, and finish loudness in ffmpeg at about −14 LUFS / −1 dBTP. AI music is a fallback only: ElevenLabs Music (licensed training, commercial use from $6/mo, API) or Google Lyria via Vertex AI. Avoid Suno (UMG and Sony filed a second suit on 18 Sep 2026 covering 60,202 recordings; Pro is capped at 20 downloads/month) and Udio (no downloads since Oct 2025).
- **Instagram trending audio is a manual, last-step choice.** The agent can only cut to a beat grid (a known BPM) or to a reference copy you bought, then export without music. You add the sound in the app. In Germany, GEMA's licence with Meta covers private, non-commercial use of the Instagram music library only. A Reel uploaded with a commercial song baked in can be re-attributed or muted at any time.
- **Resolve's own music AI (beat detector, music editor, AI Audio Assistant) is useful for your manual review but is not scriptable.** Fairlight is also mostly closed to scripting: no per-clip volume automation, EQ or fades. Do ducking, crossfades, highpass and loudness in ffmpeg/Python before import, or apply Fairlight presets wholesale (Resolve 20.2.2+). Do not run speech denoisers (DeepFilterNet, Voice Isolation) on ambience: they are built to remove exactly the street and sea sound you want to keep.

## Key Findings

- **Licensed libraries are the only option that is fully automatable and clearly legal for Instagram.** Epidemic Sound's MCP server exposes tools including SearchRecordings, EditRecording (recut to a target duration), DownloadRecording, stems and sound effects. Claude Code connects with an API key: `claude mcp add -s user --transport http epidemic-sound https://www.epidemicsound.com/a/mcp-service/mcp`. Downloading and publishing requires a paid subscription. The full Partner API is gated behind a partnership agreement, but you don't need it.
- **The AI-music market split in late 2025.** Udio settled with UMG and on 29 Oct 2025 announced "Starting today, downloads from the platform will be unavailable"; UMG said creations would be "controlled within a walled garden" (Billboard reported a brief 48-hour download window from 3 Nov 2025). Suno settled with Warner (Nov 2025), but per Suno's downloads-policy update the caps went live on 3 Sep 2026 ("Pro: 20 downloads per month; Premier: 60 downloads per month"; Digital Music News puts Pro at $8 a month), and its ToS no longer calls users the owners of their output. Per Variety, UMG and Sony filed a second, 45-page suit on 18 Sep 2026 in the U.S. District Court for the District of Massachusetts. It covers 60,202 recordings and targets Suno's v6 model (launched 9 Sep 2026), arguing that training a new model on an infringing model's outputs "launders" the infringement. ElevenLabs' Eleven Music API page says it is "Trained on licensed data and cleared for broad commercial use" (TechCrunch names Merlin Network and Kobalt as the licensing partners), from the Starter tier ($6/mo), except film, TV and games.
- **GEMA (Germany): private, non-commercial creators need to do nothing when using Instagram's music library.** GEMA's magazine (25 Jun 2024) says GEMA grants Meta's platforms the online rights through its subsidiary ICE, on the principle that the platforms, not the uploaders, are responsible for the use. GEMA says it has never sent warning letters to uploaders, but labels and publishers holding master rights may act independently. As soon as your Reels become commercial (brand deals, a business account, ads), the library licence no longer covers you.
- **Beat tracking: Beat This! (CPJKU, ISMIR 2024) is the modern default.** madmom's PyPI release (0.16.1, 2018) does not install on Python ≥3.10. BeatNet and allin1 depend on madmom, and basic-pitch officially stops at Python 3.11. On Python 3.12 / M2, librosa (1.0.0, Aug 2026) and Beat This! install cleanly; most others need forks.
- **Instagram publishes no official loudness target.** The consistent practitioner target is about −14 LUFS integrated and −1 dBTP true peak, with AAC stereo 48 kHz at 128 kbps or more in the upload. Instagram re-encodes to about 128 kbps AAC. Instagram's Help Centre says it will "automatically change attribution from Original Audio to the artist and song title" when it detects licensed audio, and that audio "can become muted as a result of any changes made to these agreements."

## Table A: Music sources for Instagram Reels

| Source | Legal status for IG (Berlin) | Cost (Oct 2026) | Agent-automatable? | Pros | Cons | Verdict |
|---|---|---|---|---|---|---|
| **Instagram library / trending audio, added in the app** | Licensed by Meta for **personal, non-commercial** use. GEMA confirms private creators need do nothing. Not cleared for ads or branded content. Business accounts get a reduced catalogue (Meta Sound Collection). Audio can be muted later if rights deals change. | Free | **No.** You add it on the phone. The agent can't fetch the file and there is no publishing API for library music. | Trend reach; zero cost; legally clean for private use | No file to cut against; the cut has to be redone by hand in the app; mute risk; becomes illegal if you go commercial | **Manual add-on only** (Flow 2) |
| **Copyrighted song baked into the upload** (bought on iTunes etc.) | Buying the track does **not** give sync rights. Rights Manager may re-attribute it to the library version or mute it. GEMA's licence covers composition online rights for private use, but label master rights remain with the label. | Price of the track | Yes technically, but legally grey | Precise cut | Mute/strike risk; no protection if commercial | **Don't publish.** Use only as a private reference for cutting. |
| **Epidemic Sound** | Direct licence (no PRO involved). Creator plan covers 1 channel per platform including Instagram. Content published while subscribed stays cleared. Pro tier needed for ads or client work. | Creator $9.99/mo annual / $17.99 monthly; Pro $16.99 annual / $39.99 monthly | **Yes. Best option.** Official MCP server (beta): search, similar-track search, `EditRecording` to a target duration, download stems, sound effects | More than 55,000 tracks and 250,000 sound effects (per Epidemic Sound's MCP page), stems, track adaptation, agent-native | Subscription lock-in; 1 channel per platform | **Primary recommendation** |
| **Artlist** | "Music & SFX Social" licence: 1 personal channel per platform including Instagram; no client work | $9.99/mo annual / $14.99 monthly | Partial: "Artlist MCP" is listed with the Max/AI plans ($39.99/mo). No self-serve catalogue API on the Social plan. | High-quality cinematic catalogue; stems on some tracks | Agent access only on the pricier plan; fewer stems | Good alternative if you prefer its sound |
| **Uppbeat** | All downloads (including free) cleared for YouTube/TikTok/Instagram, **with attribution** on the free plan. Paid plans get a perpetual licence for content published while subscribed. | Free (3 downloads/mo); paid prices vary by source ($6.99–$8.99 Essentials) | No API found; manual download | Cheap; free tier | Attribution needed on free; credit codes per video | Budget fallback, manual only |
| **Musicbed** | Not researched in this pass | Not verified | No API known | Premium cinematic sound | Pricier; not verified | Not assessed |
| **ElevenLabs Music** | Trained on licensed data; commercial use from Starter ($6/mo). Self-serve excludes film, TV and games (Enterprise only). No artist names or lyrics in prompts. | Plans from $6/mo; API sources conflict ($0.15/min on ElevenLabs' API page vs $0.30–$0.50 in third-party write-ups) | **Yes.** REST API with length and section control; instrumental mode | Cleanest licensing story among the AI generators; exact length control | Quality for "travel/lo-fi" is good but generic; per-minute cost | **Best AI option** |
| **Google Lyria (Vertex AI)** | Google-provided; SynthID watermark on outputs. Terms are per Google Cloud. | Lyria 2 (`lyria-002`): $0.06 per 30 s clip; Lyria 3 Clip $0.04 and Pro $0.08 per request (third-party listing) | **Yes.** REST `predict`; Lyria 2 returns a 48 kHz WAV, 30 s, instrumental only | Cheap; seeds give reproducibility; negative prompts | Lyria 2 clips are 30 s (you must loop or stitch them for 60 s); GCP setup | Good for ambient beds |
| **Suno** | Paid plans grant commercial use "subject to limitations". Users are "generally not considered the owner". Warner settled; UMG and Sony sued again on 18 Sep 2026. | Pro about $8–10/mo, 20 downloads/mo (Premier 60) | No official public API (third-party wrappers only) | Best-sounding songs with vocals | Live litigation; retroactive download caps; ownership ambiguity | **Avoid for a growing account** |
| **Udio** | Licensed walled garden after the UMG deal | $10–30/mo | No: downloads of audio, video and stems disabled since Oct 2025 | — | Can't export at all | **Not usable** |
| **Stable Audio / MusicGen (local)** | Not verified in this pass. MusicGen weights historically carried a non-commercial licence; check before use. | — | Local inference is heavy on 8 GB RAM | — | RAM; licence uncertainty | **Not worth it on an M2 with 8 GB** |
| **Resolve Studio AI Music Editor / Beat Detector** | N/A (edits music you already have) | Included in Studio | **No API found.** Use them in your manual review pass. | Live Trim finds natural edit points; beat markers snap cuts | Not scriptable | Use by hand, not from the agent |

## Table B: Beat and structure detection, and beat-sync tools

| Tool | Link | License | Runs on M2 8 GB / Py 3.12? | Accuracy notes | How an agent calls it | Last release / maintenance |
|---|---|---|---|---|---|---|
| **Beat This!** (CPJKU) | github.com/CPJKU/beat_this | MIT | **Yes.** `pip install beat-this`; v1.1.0 added support for non-CUDA accelerators; CPU fallback | State of the art at ISMIR 2024 "without DBN postprocessing"; gives beats and downbeats. Optional DBN needs madmom from git. | CLI or `from beat_this.inference import File2Beats` | v1.1.0 (maintenance release); repo updated 28 May 2026. **Active.** |
| **librosa** | pypi.org/project/librosa | ISC | **Yes.** Pure-Python wheel | Classic DP beat tracker; weaker than neural trackers on rubato or ambient tracks. Strong for onset strength, RMS/energy curves and spectral novelty. | Python lib | 1.0.0, 11 Aug 2026. **Active.** 1.0 removes deprecated 0.x APIs. |
| **all-in-one (allin1)** | github.com/mir-aidj/all-in-one | MIT | **Original: no.** Breaks on madmom (Py ≥3.10) and NATTEN 0.21 | Gives BPM, beats, downbeats and labelled sections (intro/verse/chorus…) in one model. Uses Demucs internally. Feed it WAV, not MP3 (20–40 ms offset). | Python / CLI | 2024 PyPI release; stuck on dependencies |
| **all-in-one-infer** (fork) | github.com/openmirlab/all-in-one-infer | MIT (fork) | **Yes, plain PyPI install.** Replaces madmom with madmom-infer; no NATTEN | Same models as allin1 | `pip install all-in-one-infer`; Python API with explicit `load()/release()` for memory | 3.1.0 line, 2026. **Active fork.** |
| **all-in-one-fix** | pypi.org/project/all-in-one-fix | MIT | Py 3.9–3.12; still pulls madmom from git | Same | pip | Fork; less clean than -infer |
| **madmom** | github.com/CPJKU/madmom | BSD-3 code; models non-commercial | **No** from PyPI (0.16.1, 2018). Git `main` needs Cython and a compiler. | Reference RNN+DBN beat and downbeat tracking | Python | **Stale.** 0.17 never released |
| **madmom-infer** | github.com/openmirlab/madmom-infer | BSD-style (port) | **Yes.** Pure numpy, numpy 2.x | Inference-only port of madmom's RNN/DBN | Python | 2026, active |
| **BeatNet** | github.com/mjhydri/BeatNet | CC-BY-4.0 | Wheel installs but needs madmom (blocked) and PortAudio/pyaudio for live mode | Joint beat/downbeat/meter, online-capable | Python | 1.1.3, Nov 2023. **Stale.** |
| **Essentia** | pypi.org/project/essentia | **AGPL-3.0** | Latest dev build (May 2026) ships only cp314 wheels; cp312 arm64 unconfirmed | Rich descriptors (RhythmExtractor, loudness, danceability) | Python | 2.1b6.dev1438, May 2026 (pre-release) |
| **aubio** | aubio.org | GPL-3.0+ | **No wheels.** Source only; known Py 3.12 build failures. The `aubio-ledfx` fork (Oct 2026) has wheels. | Fast onset/tempo; lower accuracy | CLI `aubio beat` / Python | 0.4.9, Feb 2019. **Abandoned upstream.** |
| **Spotify Basic Pitch** | pypi.org/project/basic-pitch | Apache-2.0 | **No.** Officially Py 3.7–3.11, and "for Mac M1… only python 3.10" | Polyphonic note transcription, **not** beat tracking. Irrelevant to cutting. | — | 0.4.0, Aug 2024; inactive. **Skip.** |
| **Demucs** (stems) | github.com/adefossez/demucs | MIT | Runs on CPU/MPS but is heavy; one 60 s clip at a time on 8 GB | htdemucs: drums stem → cleaner beat and onset detection | CLI `demucs -n htdemucs --two-stems=drums` | Meta repo archived 1 Jan 2025; author's fork shipped v4.1.0 (Jul 2026). Maintenance mode. |
| **Resolve AI Detect Music Beats** | Built into Resolve Studio 20+ | Proprietary | Yes (in-app) | Places beat markers on a music clip; snap to nearest frame | **GUI only.** No scripting method found | Resolve 20+ |
| **BeatEdit for Resolve** | aescripts.com/beatedit-for-davinci-resolve | Paid (aescripts) | Yes; supports Resolve 17–21 | Beat-detection algorithm from Univ. of Porto / Univ. of Victoria; colour-coded markers, clicks or subtitles | GUI plugin; not agent-callable | Current |
| **CutClaw** (research) | github.com/GVCLab/CutClaw · arXiv 2603.29664 | CC BY-NC-SA 4.0 (paper) | Multi-agent LLM pipeline aimed at hours-long footage; overkill | Joint "instruction + rhythm" optimisation; editor and reviewer agents | Python research code | Mar 2026 |
| **MVAA "Let Your Video Listen to Your Music!"** (research) | arXiv 2506.18881 · ACM MM 2025 | Research | **No.** Diffusion inpainting on a GPU (re-times motion by generating frames) | Matches motion peaks to beats | — | Oct 2025. Interesting, not practical. |

**How to express the cuts for Resolve (the recommended algorithm):**
1. Run Beat This! on a WAV → `beats[]`, `downbeats[]`. Run all-in-one-infer → `segments[]` with labels. Compute an energy curve with librosa (RMS / onset strength in 0.5 s windows).
2. Choose the cut grid by energy. In low-energy sections (intro), cut every 2 bars (8 beats). In mid-energy sections, cut every bar. In "drop" or chorus sections, cut every 2 beats; use 1 beat only for a short burst. Find the drop as the largest positive jump in RMS that coincides with a segment boundary.
3. Put the hook (first 1–2 s) before the first downbeat, or start the music at a phrase boundary so the first cut lands on downbeat 1.
4. Snap each cut to a frame: `frame = round(t * fps)`. Shift cuts 1–2 frames **early** so the visual change reads as on the beat. This is common editor practice, not a measured spec.
5. Write the result to Resolve with `timeline.AddMarker(frame, "Blue", "beat", "", 1)` for the review markers. Build the edit by appending clips with explicit in/out points (`mediaPool.AppendToTimeline([{mediaPoolItem, startFrame, endFrame, recordFrame, trackIndex}])`), or generate an FCPXML/EDL and import it. Keep the music clip on A1 and ambience on A2.

## Table C: Sound cleanup and normalisation tools

| Tool | Link | License / price | M2 8 GB | Notes for walk Reels | How the agent calls it | Status |
|---|---|---|---|---|---|---|
| **ffmpeg `loudnorm`** (EBU R128) | ffmpeg.org/ffmpeg-filters.html | LGPL/GPL, free | Yes, trivial | Two-pass: measure, then apply `I=-14:TP=-1:LRA=11`. Do it on the final mix. | CLI | Active |
| **ffmpeg `highpass` / `lowpass`** | same | free | Yes | `highpass=f=80–120` removes most wind rumble and handling noise from iPhone/Osmo audio while keeping footsteps and sea | CLI | Active |
| **ffmpeg `afftdn` / `anlmdn`** | same | free | Yes | Gentle broadband hiss reduction (`afftdn=nr=6–10`). Use more and it makes ambience sound "underwater". | CLI | Active |
| **ffmpeg `sidechaincompress`** | same | free | Yes | Not needed for music-over-ambience, since ambience is the bed. Use **static gain** (ambience at −18 to −24 dB under music) plus volume automation at the hook and outro. Real sidechain ducking only matters once you add speech. | CLI | Active |
| **ffmpeg `acrossfade` / `afade`** | same | free | Yes | 10–40 ms fades on every ambience cut stop clicks; 150–500 ms crossfades blend street → sea | CLI | Active |
| **Resolve Fairlight** | Resolve Studio 21.1.1 | Included | Yes | Clip volume, fades, EQ and dynamics are **not scriptable**. `GetFairlightPresets` / `ApplyFairlightPresetToCurrentTimeline` apply a saved mix wholesale (20.2.2+). Voice-isolation state can be read and toggled. The AI Audio Assistant is not scriptable. | Python API (limited) | Active |
| **Resolve Voice Isolation / Dialogue Separator FX** | Resolve Studio | Included | Yes | Built for **dialogue**. Dialogue Separator has voice / background / ambience controls, which could tame wind on speech later. On walk ambience it removes what you want to keep. | GUI; isolation toggle via API | Active |
| **DeepFilterNet 3** | github.com/Rikorose/DeepFilterNet | MIT/Apache, free | Yes (Rust binary `deep-filter`; 48 kHz WAV only) | **Speech** enhancer. Wrong tool for ambience; useful only once there is talking-to-camera | CLI | v0.5.x; slow-moving |
| **Adobe Podcast Enhance / Krisp** | — | Paid SaaS | Cloud | Speech-only by design; out of scope until voice is added (and voiceover is excluded from this brief) | Web/app | Not assessed in depth |
| **Demucs** | github.com/adefossez/demucs | MIT | Heavy | Not for ambience. Use it to pull a drums stem for beat detection, or to drop the vocal stem from a licensed song | CLI | Maintenance |
| **pyloudnorm** (for in-Python measurement) | — | MIT | Yes | Optional: measure LUFS per segment in Python | Python | — |

**Concrete ambience chain per clip** (run in ffmpeg before import, so the agent controls it fully):
`highpass=f=100, afftdn=nr=8:nf=-40, afade=t=in:d=0.03, afade=t=out:st=<dur-0.03>:d=0.03, volume=-20dB`
Then mix with the music and run final `loudnorm=I=-14:TP=-1:LRA=11` (two-pass) at 48 kHz stereo. Export AAC at 256–320 kbps so Instagram's re-encode starts from a near-transparent source.

## Instagram audio processing (what is known in 2026)

| Topic | Finding | Confidence |
|---|---|---|
| Codec / bitrate | AAC; playback variants top out around 128 kbps stereo. Upload at 256–320 kbps, 48 kHz. | Medium: third-party spec sheets, no Meta spec page |
| Loudness | Instagram publishes **no** exact target. About −14 LUFS integrated / −1 dBTP is the consistent practitioner advice. Pages claiming an "official Instagram LUFS" should be treated with suspicion. | Medium |
| Stereo vs mono | Most playback is on mono phone speakers. One blog claims Instagram "often collapses stereo to mono" (unverified). Mono-check the mix: avoid wide, phase-y ambience. | Low |
| Copyright detection | Meta Rights Manager matches uploaded audio. Detected licensed audio gets its attribution changed from "Original audio" to the song. Tracks can be **muted later** "as a result of any changes made to these agreements". The post stays viewable. | High (Instagram Help Centre) |
| What triggers mutes | Commercial songs on business accounts; boosting or promoting a Reel with library music; user-uploaded copies of label tracks; rights-holder withdrawals | Medium–high |

## Section D: Two end-to-end flows

### Flow 1: Music chosen in the edit (recommended default)
1. **Probe:** `ffprobe` each clip for duration, fps, colour transfer (HLG/PQ/D-Log M) and audio channels. Write the results to `clips.json`.
2. **Script:** Claude drafts the order, hook, overlays and caption, plus a **music brief** (mood, BPM range, target length = sum of planned shots, energy shape such as "calm intro → lift at 0:08").
3. **Source music:** call the Epidemic Sound MCP tool `SearchRecordings` with the brief, shortlist 3 tracks, and ask you to pick one (or auto-pick). Call `EditRecording` to a target length (e.g. 45 s) → `PollEditRecordingJob` → `DownloadRecordingEdit` as WAV, plus stems if useful. Log the track ID and licence date in `music_license.json`.
   - *AI fallback:* ElevenLabs Music API (instrumental, exact length) or Lyria 2 (30 s clips, stitched).
4. **Analyse:** Beat This! → beats/downbeats. all-in-one-infer → sections. librosa → energy curve. Optionally run Demucs on the drums stem if the track is ambient and beats are unclear.
5. **Plan cuts:** apply the energy-to-cut-grid rule above. Assign clips to slots; trim each clip's in-point to its best motion moment. Output `cuts.json` (frame-accurate at timeline fps, 30 or 60).
6. **Prep ambience:** for each clip, run the ffmpeg chain above and export `amb_XX.wav`.
7. **Build in Resolve (Python API):** create a 1080×1920 timeline, append video clips with in/out points, put the music on A1 and ambience on A2, add beat markers via `AddMarker`, and add Text+ overlays and transitions (covered in other tasks). If you keep a saved Fairlight preset, apply it.
8. **Human review:** you tweak in Resolve. Resolve's Beat Detector and AI Music Editor are available here manually.
9. **Render and master:** render 1080×1920 with the audio intact. Then run a two-pass ffmpeg `loudnorm` to −14 LUFS / −1 dBTP and remux AAC at 256–320 kbps (or master inside Resolve with a loudness meter).
10. **Publish** with "Original audio" (rename it if you like). Keep the Epidemic licence log in case of a claim.

### Flow 2: Music added in Instagram (trending audio)
1. **You pick the sound in the app first.** Note its tempo and the exact start offset you'll use. The agent cannot legally download Instagram library audio.
2. **Give the agent a beat grid, not the file:** either (a) BPM plus the first-downbeat offset (tap tempo, or public BPM metadata), or (b) a copy you bought (iTunes, Bandcamp), used **only locally** as a cutting reference.
3. The agent runs Flow 1 steps 1–2 and 4–7 against the reference, so cuts land on the grid. **Mute the music track before render.** Keep only the ambience bed at about −20 to −24 LUFS-equivalent, so the trending track sits on top without clashing.
4. Render 1080×1920 with ambience only, ending exactly at the planned length.
5. **On the phone:** upload, add the trending sound, set the same start offset, and set the music/original-audio balance (original audio low). Check sync by eye on 2–3 hard cuts.
6. **Does the cut survive?** Only if the in-app start offset matches your reference and Instagram's version is the same edit and tempo as the one you bought. Expect drift of a few frames; radio edits and sped-up versions break it. Budget time for manual nudging.
7. **Keep a fallback:** if the sound is later muted, the Reel still plays with your ambience bed, which is better than silence.

## Section E: Open legal and practical risks

| Risk | Detail | Mitigation |
|---|---|---|
| **Personal → commercial drift** | GEMA's and Meta's library licence covers only private, non-commercial use. Brand deals, affiliate links or a business account remove that cover. German law (§ 6 UrhRDaG) extends platform licences to users who are non-commercial or earn no significant revenue. | Move to Epidemic Sound or Artlist (Pro tier for ads or client work) before monetising |
| **Master rights vs GEMA** | GEMA covers compositions; labels hold master rights and enforce on their own. GEMA "has no influence" over them. | Never bake commercial songs into uploads |
| **Retroactive muting** | Instagram may mute library audio when deals change | Keep an ambience bed; prefer licensed library music for evergreen Reels |
| **AI-music litigation** | Suno: UMG/Sony second suit filed 18 Sep 2026 (per Variety, 60,202 recordings, targeting v6); ToS ownership softened; caps retroactive. Udio: no exports. | Use ElevenLabs Music or Lyria; avoid prompts naming artists; keep generation logs |
| **AI music matched as someone else's track** | Detection systems can false-match generated tracks; one guide lists "AI-generated music matching existing works" as a mute reason | Keep the licence and generation receipts; dispute through Rights Manager |
| **Subscription lapses** | Epidemic and Uppbeat: content *published* while subscribed stays cleared, but new uploads after cancelling are not | Don't stockpile downloads to publish later |
| **Tool rot on Py 3.12** | madmom, BeatNet, aubio and basic-pitch are stale; essentia's wheels lag | Pin Beat This!, librosa 1.0, all-in-one-infer and madmom-infer in `requirements.txt`; run Demucs only on demand |
| **8 GB RAM** | allin1 runs Demucs internally; running it alongside Resolve risks swapping | Run analysis with Resolve closed or idle; release models (`release()`) between steps |
| **Resolve API gaps** | No scripted clip volume, fades or EQ; the Beat Detector and Music Editor are GUI-only | Pre-process audio in ffmpeg; use Fairlight presets; keep the manual review step |

## Caveats
- Prices come from third-party trackers verified June–July 2026, plus vendor pages. Uppbeat's and ElevenLabs' API prices conflict between sources; check the live pricing pages.
- Musicbed, Stable Audio and Krisp were not verified in this pass.
- Instagram's loudness and mono behaviour is inferred by practitioners, not documented by Meta.
- The Flow 2 sync workflow is creator practice, not a feature Meta documents.
