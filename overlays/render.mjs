#!/usr/bin/env node
// Render one text overlay as transparent ProRes 4444.
//
//   node render.mjs --spec spec.json --out overlay.mov [--canvas landscape|portrait|WxH] [--strict]
//   npm run render -- --spec spec.json --out overlay.mov
//
// spec.json: { "text": "...", "type": "hook|place|fact|line", "duration_s": 3,
//              "style_path": "../style.json", "preset": "editorial-serif", "canvas": "landscape" }
// Canvas: --canvas > spec.canvas > style.json canvas. A name picks style.json
// canvases.<name>; WxH takes the geometry of the preset with the same aspect ratio
// (cf.canvas.resolve is the Python twin). The preset's safe_zone, overlay_positions
// and slots replace the top-level ones; with overlay_positions every overlay preset
// takes its placement from there (role_placement), and designScale = width /
// reference_width (2 at 2160x3840 and at 3840x2160).
// `preset` is optional; it defaults to style.json typography.preset, then "legacy".
// Optional `anchor` (a slot name from src/slots.json, e.g. "lower-left") overrides
// the preset's placement; optional `scrim` (0..1) overrides its scrim strength;
// optional `in_frames` / `out_frames` (0 = none) override the fade lengths.
// A "\n" in `text` is a forced line break.
// Relative style_path resolves against the spec file's folder; relative --spec and
// --out resolve against the caller's cwd (INIT_CWD under npm run).
// Last stdout line is a JSON summary; exit 0 ok, 1 render failed, 2 bad input,
// 3 safe-zone/text warning with --strict.
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CALLER_CWD = process.env.INIT_CWD || process.cwd();
const TYPES = ["hook", "place", "fact", "line"];
const CONCURRENCY = 2;
const LOCK = path.join(os.tmpdir(), "cf-overlays-render.lock");

const die = (code, msg) => {
  console.error(`render.mjs: ${msg}`);
  process.exit(code);
};

const parseArgs = (argv) => {
  const a = { strict: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--spec") a.spec = argv[++i];
    else if (k === "--out") a.out = argv[++i];
    else if (k === "--canvas") a.canvas = argv[++i];
    else if (k === "--strict") a.strict = true;
    else if (k === "-h" || k === "--help") a.help = true;
    else die(2, `unknown argument ${k}`);
  }
  return a;
};

const args = parseArgs(process.argv.slice(2));
if (args.help || !args.spec || !args.out)
  die(2, "usage: node render.mjs --spec spec.json --out file.mov [--canvas landscape|portrait|WxH] [--strict]");

const specPath = path.resolve(CALLER_CWD, args.spec);
const outPath = path.resolve(CALLER_CWD, args.out);
let spec;
try {
  spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
} catch (e) {
  die(2, `cannot read spec ${specPath}: ${e.message}`);
}

if (typeof spec.text !== "string" || !spec.text.trim()) die(2, "spec.text must be a non-empty string");
if (!TYPES.includes(spec.type)) die(2, `spec.type must be one of ${TYPES.join("|")}`);
if (!(typeof spec.duration_s === "number" && spec.duration_s > 0)) die(2, "spec.duration_s must be a positive number");
if (typeof spec.style_path !== "string") die(2, "spec.style_path must be a path to style.json");
if (spec.preset !== undefined && (typeof spec.preset !== "string" || !spec.preset.trim()))
  die(2, "spec.preset must be a non-empty string when present");

if (spec.canvas !== undefined && (typeof spec.canvas !== "string" || !spec.canvas.trim()))
  die(2, "spec.canvas must be a canvas name or WxH when present");

const stylePath = path.resolve(path.dirname(specPath), spec.style_path);
let baseStyle;
try {
  baseStyle = JSON.parse(fs.readFileSync(stylePath, "utf8"));
} catch (e) {
  die(2, `cannot read style ${stylePath}: ${e.message}`);
}
if (!baseStyle.canvas) die(2, `style.json is missing "canvas"`);

// --- canvas resolution (mirror of src/cf/canvas.py resolve / overlay_style) ---
const canvasPresets = Object.fromEntries(
  Object.entries(baseStyle.canvases ?? {}).filter(([k, v]) => !k.startsWith("_") && v && typeof v === "object"),
);
const sameAspect = (a, b) => a[0] * b[1] === a[1] * b[0];
const defaultPreset = () => {
  const c = baseStyle.canvas;
  for (const [name, p] of Object.entries(canvasPresets))
    if (p.width === c.width && p.height === c.height) return [name, { ...c, ...p }];
  return [null, c];
};
const resolveCanvas = (specText) => {
  const t = (specText ?? "").trim();
  if (!t) return defaultPreset();
  if (canvasPresets[t]) return [t, canvasPresets[t]];
  const m = /^\s*(\d+)\s*[xX×]\s*(\d+)\s*$/.exec(t);
  if (!m) die(2, `unknown canvas "${t}"; style.json canvases has ${Object.keys(canvasPresets).join(", ")} (or give WxH)`);
  const size = [Number(m[1]), Number(m[2])];
  if (size.some((n) => n <= 0 || n % 2)) die(2, `canvas ${t}: width and height must be positive and even`);
  const [dn, dc] = defaultPreset();
  if (sameAspect(size, [dc.width, dc.height])) return [dn, { ...dc, width: size[0], height: size[1] }];
  for (const [name, p] of Object.entries(canvasPresets))
    if (sameAspect(size, [p.width, p.height])) return [name, { ...p, width: size[0], height: size[1] }];
  die(2, `canvas ${t}: no style.json canvases preset has that aspect ratio`);
};
const canvasSpec = args.canvas ?? spec.canvas;
const [canvasName, cv] = resolveCanvas(canvasSpec);
const style = {
  ...baseStyle,
  canvas: {
    width: cv.width,
    height: cv.height,
    fps: cv.fps ?? baseStyle.canvas.fps,
    reference_width: cv.reference_width ?? baseStyle.canvas.reference_width ?? 1080,
    ...(canvasName ? { preset: canvasName } : {}),
  },
  safe_zone: cv.safe_zone ?? baseStyle.safe_zone,
  overlay_positions: cv.overlay_positions ?? baseStyle.overlay_positions,
  ...(cv.slots ? { slots: cv.slots } : {}),
  ...(cv.overlay_positions ? { role_placement: "overlay_positions" } : {}),
};
for (const key of ["canvas", "safe_zone", "typography", "colors", "overlay_positions", "animation"])
  if (!style[key]) die(2, `style.json is missing "${key}"`);
if (!style.overlay_positions[spec.type]) die(2, `style.overlay_positions has no "${spec.type}"`);
const refWidth = style.canvas.reference_width ?? 1080;
if (!(Number.isFinite(refWidth) && refWidth > 0)) die(2, "style.canvas.reference_width must be a positive number");
// One scale factor for the whole design (src/style.ts designScale).
const designScale = style.canvas.width / refWidth;

const preset = (spec.preset ?? style.typography.preset ?? "legacy").trim();
// The catalogue lives in src/presets.ts; check the name here so a typo is exit 2,
// not a failed render.
const presetSrc = fs.readFileSync(path.join(HERE, "src", "presets.ts"), "utf8");
const knownPresets = ["legacy", ...[...presetSrc.matchAll(/^  "([a-z0-9-]+)": \{$/gm)].map((m) => m[1])];
if (!knownPresets.includes(preset)) die(2, `unknown preset "${preset}"; known: ${knownPresets.join(", ")}`);

const slots = style.slots ?? JSON.parse(fs.readFileSync(path.join(HERE, "src", "slots.json"), "utf8"));
const knownSlots = Object.keys(slots).filter((k) => !k.startsWith("_"));
if (spec.anchor !== undefined && !knownSlots.includes(spec.anchor))
  die(2, `unknown anchor "${spec.anchor}"; known: ${knownSlots.join(", ")}`);
if (spec.scrim !== undefined && !(typeof spec.scrim === "number" && spec.scrim >= 0 && spec.scrim <= 1))
  die(2, "spec.scrim must be a number in 0..1");

// Optional in_frames / out_frames (int >= 0) replace style.animation in/out frames for
// this overlay; 0 = no fade on that side (a list item that cuts on with its shot).
for (const k of ["in_frames", "out_frames"])
  if (spec[k] !== undefined && !(Number.isInteger(spec[k]) && spec[k] >= 0))
    die(2, `spec.${k} must be an integer >= 0`);
if (spec.in_frames !== undefined || spec.out_frames !== undefined)
  style.animation = {
    ...style.animation,
    in: { ...style.animation.in, ...(spec.in_frames !== undefined ? { frames: spec.in_frames } : {}) },
    out: { ...style.animation.out, ...(spec.out_frames !== undefined ? { frames: spec.out_frames } : {}) },
  };

const fps = style.canvas.fps;
const durationInFrames = Math.round(spec.duration_s * fps);
if (durationInFrames < 1) die(2, "duration_s is shorter than one frame");

const warnings = [];
const words = spec.text.trim().split(/\s+/).length;
const maxWords = style.typography.max_words_per_line * style.typography.max_lines;
if (words > maxWords)
  warnings.push(`TEXT_OVERFLOW ${words} words > ${maxWords} (max_words_per_line x max_lines)`);
const minHold = style.animation.min_hold_s;
if (minHold && spec.duration_s < minHold)
  warnings.push(`SHORT_HOLD duration_s ${spec.duration_s} < min_hold_s ${minHold}`);

// One render at a time on this machine: wait for any other render.mjs to finish.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const acquireLock = async () => {
  const deadline = Date.now() + 15 * 60 * 1000;
  for (;;) {
    try {
      fs.writeFileSync(LOCK, String(process.pid), { flag: "wx" });
      return;
    } catch {
      const pid = Number(fs.readFileSync(LOCK, "utf8") || 0);
      let alive = false;
      try {
        process.kill(pid, 0);
        alive = true;
      } catch {}
      if (!alive) {
        fs.rmSync(LOCK, { force: true });
        continue;
      }
      if (Date.now() > deadline) die(1, `another render (pid ${pid}) holds ${LOCK}`);
      await sleep(1000);
    }
  }
};
const releaseLock = () => {
  try {
    if (fs.readFileSync(LOCK, "utf8") === String(process.pid)) fs.rmSync(LOCK);
  } catch {}
};

const propsFile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "cf-overlay-")), "props.json");
fs.writeFileSync(propsFile, JSON.stringify({
    text: spec.text,
    type: spec.type,
    durationInFrames,
    style,
    preset,
    ...(spec.anchor !== undefined ? { anchor: spec.anchor } : {}),
    ...(spec.scrim !== undefined ? { scrim: spec.scrim } : {}),
  }));
fs.mkdirSync(path.dirname(outPath), { recursive: true });

const cliArgs = [
  "--no-install",
  "remotion",
  "render",
  "src/index.ts",
  "Overlay",
  outPath,
  `--props=${propsFile}`,
  "--codec=prores",
  "--prores-profile=4444",
  "--pixel-format=yuva444p10le",
  "--image-format=png",
  `--concurrency=${CONCURRENCY}`,
  "--color-space=bt709",
  "--overwrite",
  "--log=verbose",
];

await acquireLock();
process.on("exit", releaseLock);
process.on("SIGINT", () => process.exit(130));
process.on("SIGTERM", () => process.exit(143));

const started = Date.now();
const code = await new Promise((resolve) => {
  const child = spawn("npx", cliArgs, { cwd: HERE, stdio: ["ignore", "pipe", "pipe"] });
  let tail = "";
  const onData = (stream) => (buf) => {
    const s = buf.toString();
    tail = (tail + s).slice(-8000);
    for (const line of s.split("\n")) {
      const m = /\[cf-overlay\] (WARN )?(.*)/.exec(line);
      if (m) {
        const msg = m[2].replace(/\s+$/, "");
        if (m[1] && !warnings.includes(msg)) warnings.push(msg);
        console.error(`[overlay] ${m[1] ? "WARNING " : ""}${msg}`);
      }
    }
    if (process.env.CF_OVERLAY_VERBOSE) stream.write(buf);
  };
  child.stdout.on("data", onData(process.stdout));
  child.stderr.on("data", onData(process.stderr));
  child.on("close", (c) => {
    if (c !== 0) process.stderr.write(tail);
    resolve(c ?? 1);
  });
});
fs.rmSync(path.dirname(propsFile), { recursive: true, force: true });

const summary = {
  ok: code === 0,
  out: outPath,
  type: spec.type,
  preset,
  anchor: spec.anchor ?? null,
  canvas: canvasName,
  fps,
  frames: durationInFrames,
  width: style.canvas.width,
  height: style.canvas.height,
  scale: designScale,
  render_s: Math.round((Date.now() - started) / 100) / 10,
  safe_zone_ok: !warnings.some((w) => w.startsWith("SAFE_ZONE_VIOLATION")),
  warnings,
};
console.log(JSON.stringify(summary));
if (code !== 0) process.exit(1);
if (args.strict && warnings.length) process.exit(3);
