/**
 * Defaults for `npx remotion render` / Studio. render.mjs also passes every
 * flag explicitly, so these only matter for ad-hoc CLI use.
 * All options: https://remotion.dev/docs/config
 */
import { Config } from "@remotion/cli/config";

Config.setRspack(true);
Config.setOverwriteOutput(true);
// Transparent ProRes 4444 for Resolve (docs/research/02-overlays-and-motion-graphics/result-a.md, Section C).
Config.setVideoImageFormat("png");
Config.setCodec("prores");
Config.setProResProfile("4444");
Config.setPixelFormat("yuva444p10le");
// Tag the file Rec.709 (primaries, transfer, matrix) so Resolve does not guess.
Config.setColorSpace("bt709");
// 8 GB machine shared with Resolve and other jobs.
Config.setConcurrency(2);
