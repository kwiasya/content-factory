# Working with the Resolve scripting API

Rules every skill that touches DaVinci Resolve Studio 21.1.1 follows. Rationale: `docs/adr/0001-timeline-rebuilt-from-plan.md`, evidence: `docs/research/01-resolve-scripting-api/`.

## Source of truth

The typed stub ships with Resolve:

```
/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi
```

Only methods present in the stub exist. Before calling a method you have not used in this session, grep the stub for its signature. The CHANGELOG in the same folder lists what each version added.

## Connecting

From the repo venv (`.venv`, Python 3.12). Resolve must be running with a project open; `scriptapp("Resolve")` returns `None` otherwise. Env vars:

```
RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
PYTHONPATH="$RESOLVE_SCRIPT_API/Modules"
```

All calls go through `src/cf/resolve_driver.py`: one process, one connection, a timeout on every call.

## Rebuild, never patch

The timeline is built in one pass from the plan (`AppendToTimeline` with explicit `recordFrame` and `trackIndex`). To change anything, delete the timeline and build it again from the plan. The API has no trim, move or slip.

## Read back every write

A `True` return proves nothing: settings calls drop unknown keys silently and can return `False` after a partial apply. After each write, read the value back (`GetSetting`, `GetClipProperty`, `GetProperty`, `GetStart`/`GetEnd`) and fail loudly on a mismatch. Set one key per call.

## Known gaps (do by hand in the GUI)

Trim/move/slip, speed curves, EQ and compression, Resolve FX on a clip, reading a grade back, IntelliScript, AI Music Editor, Beat Detector, Shot Match.

## Known traps

- `fu.GetCurrentComp()` is `None` until the Fusion page has been opened once in the session.
- `GetCurrentRenderMode()` switches the UI to the Deliver page.
- `SetSpeed` with `RippleTimeline: true` has deleted audio tracks in the field; leave it `false`.
- Pass `alignment` in every `AddTransition` call until smoke test S4 says otherwise.
- `InsertFusionTitleIntoTimeline` placement is unverified (S5); overlays go through Remotion on V2/V3 by default.
