---
name: resolve-smoke
description: Run the Resolve API smoke tests S1–S10 against the open Resolve and record what the API actually does. Use after installing or updating Resolve, or when a build-reel step fails in a way the rules do not predict.
---

# Resolve smoke tests

Rules and connection details: `docs/resolve-rules.md`. Test list and the claim each one checks: `docs/research/SYNTHESIS.md` §3.

## Steps

1. Confirm Resolve is running with a scratch project open (name starts with `smoke-`). Ask the user to open one if not; never run against a real project.
2. Run every test script in `tests/smoke/` in order (`S01_*.py` … `S10_*.py`) with `.venv/bin/python`. Each prints `PASS`, `FAIL` or `SKIP` plus the raw values it read back.
3. For every FAIL, grep the stub for the method and try the documented signature once more; record both attempts.
4. Write `docs/research/smoke-results.md`: a table of test, result, exact strings discovered (color space names, transition type names, where a Fusion title landed), Resolve version, date.
5. Update `docs/resolve-rules.md` where a result contradicts a rule or trap listed there.

Done when every test has a recorded result and the rules file agrees with them.
