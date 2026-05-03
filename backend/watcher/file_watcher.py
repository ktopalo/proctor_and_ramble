import asyncio
import difflib
import logging
from pathlib import Path
from typing import Callable, Awaitable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from backend.session.models import FileDelta

log = logging.getLogger(__name__)


class _Handler(FileSystemEventHandler):
    def __init__(self, callback):
        self._callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self._callback(str(Path(event.src_path).resolve()))

    def on_created(self, event):
        if not event.is_directory:
            self._callback(str(Path(event.src_path).resolve()))


class FileWatcher:
    def __init__(self, path: str, on_delta: Callable[[FileDelta], Awaitable[None]]):
        resolved = Path(path).resolve()
        self._is_dir = resolved.is_dir()
        self._path = str(resolved)
        self._on_delta = on_delta
        self._last_content: dict[str, str] = {}
        self._observer = Observer()
        self._loop: asyncio.AbstractEventLoop | None = None

        if self._is_dir:
            for f in resolved.rglob("*"):
                if f.is_file():
                    self._last_content[str(f)] = self._read_file(str(f))
        else:
            self._last_content[self._path] = self._read_file(self._path)

    def _read_file(self, path: str) -> str:
        try:
            return Path(path).read_text()
        except (FileNotFoundError, PermissionError, UnicodeDecodeError):
            return ""

    def start(self) -> None:
        self._loop = asyncio.get_event_loop()
        handler = _Handler(self._on_file_changed)
        watch_dir = self._path if self._is_dir else str(Path(self._path).parent)
        self._observer.schedule(handler, watch_dir, recursive=self._is_dir)
        self._observer.start()
        if self._is_dir:
            log.info("FileWatcher started  dir=%s  recursive=True  tracked_files=%d", self._path, len(self._last_content))
        else:
            log.info("FileWatcher started  file=%s", self._path)

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
        log.info("FileWatcher stopped")

    def _on_file_changed(self, file_path: str) -> None:
        if not self._is_dir and file_path != self._path:
            return

        new_content = self._read_file(file_path)
        last_content = self._last_content.get(file_path, "")
        diff_lines = list(
            difflib.ndiff(
                last_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
            )
        )
        meaningful = [l for l in diff_lines if not l.startswith("? ")]
        has_changes = any(l.startswith("+ ") or l.startswith("- ") for l in meaningful)
        if has_changes:
            diff = "".join(meaningful)
            self._last_content[file_path] = new_content
            added = sum(1 for l in meaningful if l.startswith("+ "))
            removed = sum(1 for l in meaningful if l.startswith("- "))
            log.info("FileWatcher delta  path=%s  +%d -%d lines", file_path, added, removed)
            delta = FileDelta(path=file_path, diff=diff)
            asyncio.run_coroutine_threadsafe(self._on_delta(delta), self._loop)
