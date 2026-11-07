# Motion kit (overlays)

Rules for the **`video-motion`** agent (and anyone it delegates to) when building code-driven video in this folder. Entered via `/produce` on motion / Tech explainer chains. Walk Reel text overlays still go through `Overlay.tsx` + `render.mjs` and `/build-reel` (`video-picture`); this file is for richer Remotion (or HyperFrames) motion work.

## Engine

1. **Remotion** is the default. Load `/remotion-best-practices` (and the branch skill it points at) before writing composition code. Drive every animation from `useCurrentFrame()` / `interpolate` — never wall-clock timers, `requestAnimationFrame`, or unsynced springs that ignore the frame.
2. **HyperFrames** only when the author asks for HyperFrames, HTML/GSAP, or a Remotion→HyperFrames port. Then read `/hyperframes` first (CLI: `/hyperframes-cli`, registry: `/hyperframes-registry`, port: `/remotion-to-hyperframes`). CLI is `npx hyperframes` from this folder.

Do not invent a third renderer. Do not drop to Resolve Fusion for motion that belongs in this kit.

## Pick from the installed kit

Before hand-rolling CSS keyframes, canvas loops, or a new npm dependency, choose the library already in `package.json` that matches the job. One library per job is enough; stack only when the brief needs two roles (e.g. Three scene + Tone bed).

| Job | Use |
|---|---|
| Scene transitions / wipes between sequences | `@remotion/transitions` and, for GLSL shader transitions, `gl-transitions` + `@gl-transitions/remotion` |
| 3D scenes, models, lights, camera | `@remotion/three` + `three` (see Remotion markup `3d`) |
| Motion design / timeline tweens beyond basic interpolate | `animejs` (seek from the current frame; no autoplay timeline) |
| Spring feel (mass, tension) under Remotion time | `@react-spring/web` only if values are derived from frame; else prefer Remotion `spring` |
| Dense 2D WebGL (sprites, filters, particle-ish 2D) | `pixi.js` |
| Generative patterns, looping backgrounds | `p5` (seed randomness; draw from frame, not `draw()` wall clock) |
| Vector paths, outlines, figure morphs | `paper` |
| Confetti / particle overlays from config | `@tsparticles/engine` + `@tsparticles/slim` |
| 2D rigid-body look | `matter-js` — step the engine from frame with a fixed seed; no live realtime loop |
| 3D physics | `@dimforge/rapier3d-compat` — same: frame-stepped, seeded |
| Music / synth / sequenced audio in the composition | `tone` (Transport and players locked to Remotion audio / frame) |
| Screen demos of products or sites | **OBS Studio** on this Mac (`/Applications/OBS.app`); capture files, then edit — do not fake a screen record in code |
| Voice-over generation | `.venv-chatterbox` + Chatterbox (`resemble-ai`); never install Chatterbox into `.venv` (it pins an older torch and breaks stable-ts) |
| Speech → captions / word timestamps | Project `.venv` + **stable-ts** (`cf.research.stablets` / `cf.metrics.speech`). Not faster-whisper. Remotion caption skills may use `@remotion/whisper-webgpu` only inside a Remotion-captions flow |

Fonts for text overlays stay on `@remotion/google-fonts` / `src/fonts.ts` as today.

## Skills map

| When | Load |
|---|---|
| Any Remotion composition work | `/remotion-best-practices` → branch skill |
| Captions from audio | `/remotion-captions` |
| HyperFrames brief or port | `/hyperframes` (and siblings above) |
| Walk Reel assembly in Resolve | `/reel` / `/build-reel` — not this kit’s freeform path |

## Done when

- The composition preview runs in Remotion Studio (`npm run dev`) or the HyperFrames preview the skill names.
- Every moving value is a function of frame (or HyperFrames seek time).
- New visual behaviour came from the table above, or you recorded in the reply why nothing there fits before adding a package.
