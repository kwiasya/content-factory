"""Local per-second metrics for Shot logs (docs/adr/0002-agent-sees-shot-log-not-frames.md).

Each module reads one 540p proxy and returns plain per-second arrays; cf.shotlog
assembles them into a `reel-shotlog/1.0` JSON.
"""
