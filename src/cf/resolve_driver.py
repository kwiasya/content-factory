"""Thin driver over the DaVinci Resolve scripting API.

Rules (docs/resolve-rules.md): one process, one connection, a timeout on every
call, read back every write. Only projects named ``smoke-*`` or ``cf-*`` may be
created or modified. Canonical 21.1 calling conventions are used throughout:
``GetSettings``/``SetSettings`` and ``GetProperties``/``SetProperties`` (the
single-key ``GetSetting``/``SetSetting``/``SetProperty`` forms are deprecated).
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

SCRIPT_API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
SCRIPT_LIB = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
ALLOWED_PREFIXES = ("smoke-", "cf-")


class ResolveError(RuntimeError):
    """A Resolve call failed, timed out, or a read-back did not match."""


def same_value(written: Any, read: Any) -> bool:
    """True if a read-back value equals what was written (strings vs numbers tolerated)."""
    if written == read or str(written) == str(read):
        return True
    try:
        return abs(float(written) - float(read)) < 1e-6
    except (TypeError, ValueError):
        return False


def is_allowed_project(name: str) -> bool:
    return any(name.startswith(p) for p in ALLOWED_PREFIXES)


class ResolveDriver:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.resolve: Any = None
        self.project: Any = None

    # -- plumbing -----------------------------------------------------------
    def call(self, fn: Callable, *args: Any, timeout: float | None = None) -> Any:
        """Run one API call in a worker thread; raise ResolveError on timeout."""
        box: dict[str, Any] = {}

        def run() -> None:
            try:
                box["value"] = fn(*args)
            except BaseException as exc:  # noqa: BLE001 - re-raised below
                box["error"] = exc

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout or self.timeout)
        if t.is_alive():
            name = getattr(fn, "__name__", repr(fn))
            raise ResolveError(f"timeout after {timeout or self.timeout}s in {name}{args!r}")
        if "error" in box:
            raise box["error"]
        return box.get("value")

    def connect(self) -> Any:
        os.environ.setdefault("RESOLVE_SCRIPT_API", SCRIPT_API)
        os.environ.setdefault("RESOLVE_SCRIPT_LIB", SCRIPT_LIB)
        modules = os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules")
        if modules not in sys.path:
            sys.path.append(modules)
        import DaVinciResolveScript as dvr  # noqa: PLC0415 - needs env first

        self.resolve = self.call(dvr.scriptapp, "Resolve")
        if self.resolve is None:
            raise ResolveError(
                "scriptapp('Resolve') returned None: is Resolve running and "
                "Preferences > System > General > External scripting using = Local?"
            )
        return self.resolve

    def _require_safe_project(self) -> Any:
        if self.project is None:
            raise ResolveError("no project loaded through get_or_create_project()")
        current = self.call(self.resolve.GetProjectManager().GetCurrentProject)
        name = self.call(current.GetName) if current else None
        if not name or not is_allowed_project(name):
            raise ResolveError(f"refusing to modify project {name!r}")
        return current

    # -- project ------------------------------------------------------------
    def get_or_create_project(self, name: str) -> Any:
        if not is_allowed_project(name):
            raise ResolveError(f"project name must start with {ALLOWED_PREFIXES}: {name!r}")
        pm = self.call(self.resolve.GetProjectManager)
        current = self.call(pm.GetCurrentProject)
        if current is not None and self.call(current.GetName) == name:
            self.project = current
            return current
        project = None
        if name in (self.call(pm.GetProjectListInCurrentFolder) or []):
            project = self.call(pm.LoadProject, name, timeout=120)
        else:
            project = self.call(pm.CreateProject, name, timeout=120)
        if project is None or self.call(project.GetName) != name:
            raise ResolveError(f"could not load or create project {name!r}")
        self.project = project
        return project

    def save(self) -> bool:
        self._require_safe_project()
        return bool(self.call(self.resolve.GetProjectManager().SaveProject))

    def set_setting_verified(self, key: str, value: Any, target: Any = None) -> Any:
        """SetSettings({key: value}) on the project (or a timeline), then read back."""
        self._require_safe_project()
        target = target or self.project
        ok = self.call(target.SetSettings, {key: value})
        got = (self.call(target.GetSettings) or {}).get(key)
        if not same_value(value, got):
            raise ResolveError(f"setting {key}: wrote {value!r}, read {got!r} (returned {ok})")
        return got

    def set_clip_property_verified(self, item: Any, key: str, value: Any) -> Any:
        """SetClipProperty on a MediaPoolItem, then read back via GetClipProperty()."""
        self._require_safe_project()
        ok = self.call(item.SetClipProperty, key, value)
        got = (self.call(item.GetClipProperty) or {}).get(key)
        if not same_value(value, got):
            raise ResolveError(f"clip property {key}: wrote {value!r}, read {got!r} (returned {ok})")
        return got

    def set_item_property_verified(self, item: Any, key: str, value: Any) -> Any:
        """SetProperties({key: value}) on a TimelineItem, then read back."""
        self._require_safe_project()
        ok = self.call(item.SetProperties, {key: value})
        got = (self.call(item.GetProperties) or {}).get(key)
        if not same_value(value, got):
            raise ResolveError(f"item property {key}: wrote {value!r}, read {got!r} (returned {ok})")
        return got

    # -- media and timelines -----------------------------------------------
    def media_pool(self) -> Any:
        return self.call(self.project.GetMediaPool)

    def walk_folders(self, folder: Any = None) -> list[Any]:
        """The folder and all its sub-folders (depth first); the root bin by default."""
        folder = folder or self.call(self.media_pool().GetRootFolder)
        out = [folder]
        for sub in self.call(folder.GetSubFolderList) or []:
            out.extend(self.walk_folders(sub))
        return out

    def get_or_create_bin(self, name: str, parent: Any = None) -> Any:
        """Sub-folder ``name`` of ``parent`` (root by default), created if missing."""
        self._require_safe_project()
        mp = self.media_pool()
        parent = parent or self.call(mp.GetRootFolder)
        for sub in self.call(parent.GetSubFolderList) or []:
            if self.call(sub.GetName) == name:
                return sub
        folder = self.call(mp.AddSubFolder, parent, name)
        if folder is None or self.call(folder.GetName) != name:
            raise ResolveError(f"AddSubFolder({name!r}) returned {folder!r}")
        return folder

    def clip_index(self) -> dict[str, list[Any]]:
        """File Path -> MediaPoolItems, over every bin of the media pool."""
        index: dict[str, list[Any]] = {}
        for folder in self.walk_folders():
            for clip in self.call(folder.GetClipList) or []:
                fp = (self.call(clip.GetClipProperty) or {}).get("File Path")
                if fp:
                    index.setdefault(fp, []).append(clip)
        return index

    def find_clip(self, path: str | Path) -> Any:
        """Return the MediaPoolItem (in any bin) whose File Path is ``path``."""
        hits = self.clip_index().get(str(path))
        return hits[0] if hits else None

    def import_media(self, paths: list[str | Path], bin_name: str | None = None) -> list[Any]:
        """Import files (reusing clips already in the pool); return items in input order.

        Clips already in the pool (matched by File Path in any bin) are reused, so a
        rebuild never duplicates media. New files go into ``bin_name`` (a sub-folder
        of the root, created if needed) or the root bin.

        Smoke S3 (21.1.1): the canonical ``MediaPool.ImportMedia([{"FilePath": p}])``
        returns None for plain movie files, so ``MediaStorage.AddItemListToMediaPool``
        is used, with the deprecated ``ImportMedia([path, ...])`` as fallback.
        """
        self._require_safe_project()
        index = self.clip_index()
        missing = [str(p) for p in paths if str(p) not in index]
        if missing:
            mp = self.media_pool()
            target = self.get_or_create_bin(bin_name) if bin_name else self.call(mp.GetRootFolder)
            if not self.call(mp.SetCurrentFolder, target):
                raise ResolveError(f"SetCurrentFolder({bin_name!r}) failed")
            storage = self.call(self.resolve.GetMediaStorage)
            items = self.call(storage.AddItemListToMediaPool, [{"media": p} for p in missing], timeout=120)
            if not items or len(items) != len(missing):
                items = self.call(mp.ImportMedia, missing, timeout=120)
            if not items or len(items) != len(missing):
                raise ResolveError(f"import returned {items!r} for {missing}")
            index = self.clip_index()
        out = [(index.get(str(p)) or [None])[0] for p in paths]
        if any(c is None for c in out):
            raise ResolveError(f"import did not yield clips for {paths}")
        return out

    def find_timeline(self, name: str) -> Any:
        for i in range(1, int(self.call(self.project.GetTimelineCount)) + 1):
            tl = self.call(self.project.GetTimelineByIndex, i)
            if tl and self.call(tl.GetName) == name:
                return tl
        return None

    def create_timeline(self, name: str, width: int, height: int, fps: float | str,
                        custom: bool = True) -> Any:
        """Delete any timeline with this name, create it empty, check res/fps, read back.

        ``custom=True`` sets ``useCustomSettings='1'`` plus res/fps on the timeline. That
        snapshots the project color settings (S3), so pass ``custom=False`` when the
        project already has the right res/fps; the read-back runs either way.
        """
        self._require_safe_project()
        mp = self.media_pool()
        old = self.find_timeline(name)
        if old is not None and not self.call(mp.DeleteTimelines, [old]):
            raise ResolveError(f"could not delete old timeline {name!r}")
        if self.find_timeline(name) is not None:
            raise ResolveError(f"timeline {name!r} still exists after DeleteTimelines")
        tl = self.call(mp.CreateEmptyTimeline, name)
        if tl is None:
            raise ResolveError(f"CreateEmptyTimeline({name!r}) returned None")
        self.call(self.project.SetCurrentTimeline, tl)
        wanted = {"timelineResolutionWidth": str(width), "timelineResolutionHeight": str(height),
                  "timelineFrameRate": str(fps)}
        if custom:
            self.set_setting_verified("useCustomSettings", "1", target=tl)
            for k, v in wanted.items():
                self.set_setting_verified(k, v, target=tl)
        got = self.call(tl.GetSettings) or {}
        bad = {k: (v, got.get(k)) for k, v in wanted.items() if not same_value(v, got.get(k))}
        if bad:
            raise ResolveError(f"timeline {name!r} settings (wanted, read): {bad}")
        return tl

    def ensure_tracks(self, timeline: Any, track_type: str, count: int,
                      names: dict[int, str] | None = None, sub_type: str | None = None) -> int:
        """AddTrack until ``timeline`` has ``count`` tracks of ``track_type``; name them; read back."""
        self._require_safe_project()
        while int(self.call(timeline.GetTrackCount, track_type)) < count:
            args = (track_type, sub_type) if sub_type else (track_type,)
            if not self.call(timeline.AddTrack, *args):
                raise ResolveError(f"AddTrack{args} returned False")
        for idx, name in (names or {}).items():
            self.call(timeline.SetTrackName, track_type, idx, name)
            got = self.call(timeline.GetTrackName, track_type, idx)
            if got != name:
                raise ResolveError(f"track {track_type}{idx} name: wrote {name!r}, read {got!r}")
        return int(self.call(timeline.GetTrackCount, track_type))

    def append(self, clip_infos: list[dict]) -> list[Any]:
        """AppendToTimeline on the current timeline; one returned item per info or raise."""
        self._require_safe_project()
        items = self.call(self.media_pool().AppendToTimeline, clip_infos, timeout=60)
        if not items:
            raise ResolveError(f"AppendToTimeline returned {items!r}")
        return list(items)

    def add_marker(self, target: Any, frame: int, color: str, name: str, note: str = "",
                   duration: int = 1, custom_data: str | None = None) -> dict:
        """AddMarker on a Timeline / TimelineItem / MediaPoolItem, then read it back."""
        self._require_safe_project()
        args = [frame, color, name, note, duration] + ([custom_data] if custom_data is not None else [])
        if not self.call(target.AddMarker, *args):
            raise ResolveError(f"AddMarker{tuple(args)} returned False")
        got = (self.call(target.GetMarkers) or {}).get(frame)
        if not got or got.get("name") != name or (custom_data is not None and got.get("customData") != custom_data):
            raise ResolveError(f"marker at {frame}: read back {got!r}")
        return got

    # -- render -------------------------------------------------------------
    def render(self, out_path: str | Path, preset: str | None = None, fmt: str | None = None,
               codec: str | None = None, settings: dict | None = None,
               poll: float = 1.0, max_wait: float = 900.0) -> dict:
        """Queue one render job of the current timeline and wait for it to finish.

        Order: preset, then format/codec, then settings (TargetDir and CustomName are
        derived from ``out_path``). Returns the final job status plus the job id.
        """
        self._require_safe_project()
        p = self.project
        out = Path(out_path).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        if preset and not self.call(p.LoadRenderPreset, preset):
            raise ResolveError(f"LoadRenderPreset({preset!r}) failed")
        if fmt and codec and not self.call(p.SetCurrentRenderFormatAndCodec, fmt, codec):
            raise ResolveError(f"SetCurrentRenderFormatAndCodec({fmt!r}, {codec!r}) failed")
        merged = {"TargetDir": str(out.parent), "CustomName": out.stem, **(settings or {})}
        if not self.call(p.SetRenderSettings, merged):
            raise ResolveError(f"SetRenderSettings({merged!r}) returned False")
        job = self.call(p.AddRenderJob)
        if not job:
            raise ResolveError("AddRenderJob returned no job id")
        if not self.call(p.StartRendering, [job]):
            raise ResolveError(f"StartRendering([{job}]) returned False")
        deadline = time.monotonic() + max_wait
        status: dict = {}
        while time.monotonic() < deadline:
            status = self.call(p.GetRenderJobStatus, job) or {}
            if status.get("JobStatus") in ("Complete", "Failed", "Cancelled"):
                break
            time.sleep(poll)
        else:
            self.call(p.StopRendering)
            raise ResolveError(f"render {job} did not finish in {max_wait}s: {status}")
        status = dict(status, JobId=job)
        if status.get("JobStatus") != "Complete":
            raise ResolveError(f"render {job} ended with {status}")
        return status
