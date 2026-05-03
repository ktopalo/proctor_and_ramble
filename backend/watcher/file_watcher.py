import asyncio
import difflib
from pathlib import Path
from typing import Callable, Awaitable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from backend.session.models import FileDelta


class _Handler(FileSystemEventHandler):
    def __init__(self, target: str, callback):
        self._target = str(Path(target).resolve())
        self._callback = callback

    def on_modified(self, event):
        if not event.is_directory and str(Path(event.src_path).resolve()) == self._target:
            self._callback()


class FileWatcher:
    def __init__(self, path: str, on_delta: Callable[[FileDelta], Awaitable[None]]):
        self._path = str(Path(path).resolve())
        self._on_delta = on_delta
        self._last_content: str = self._read()
        self._observer = Observer()
        self._loop: asyncio.AbstractEventLoop | None = None

    def _read(self) -> str:
        try:
            return Path(self._path).read_text()
        except FileNotFoundError:
            return ""

    def start(self) -> None:
        self._loop = asyncio.get_event_loop()
        handler = _Handler(self._path, self._on_file_changed)
        watch_dir = str(Path(self._path).parent)
        self._observer.schedule(handler, watch_dir, recursive=False)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()

    def _on_file_changed(self) -> None:
        new_content = self._read()
        diff_lines = list(
            difflib.ndiff(
                self._last_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
            )
        )
        # Keep only meaningful lines (added, removed, changed) — drop hints
        meaningful = [l for l in diff_lines if not l.startswith("? ")]
        has_changes = any(l.startswith("+ ") or l.startswith("- ") for l in meaningful)
        if has_changes:
            diff = "".join(meaningful)
            self._last_content = new_content
            delta = FileDelta(path=self._path, diff=diff)
            asyncio.run_coroutine_threadsafe(self._on_delta(delta), self._loop)
