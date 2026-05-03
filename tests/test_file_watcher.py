import asyncio
import pytest
from pathlib import Path
from backend.watcher.file_watcher import FileWatcher
from backend.session.models import FileDelta


@pytest.mark.asyncio
async def test_file_watcher_emits_delta_on_save(tmp_path):
    target = tmp_path / "solution.py"
    target.write_text("x = 1\n")

    received: list[FileDelta] = []

    async def on_delta(delta: FileDelta):
        received.append(delta)

    watcher = FileWatcher(path=str(target), on_delta=on_delta)
    watcher.start()

    await asyncio.sleep(0.5)
    target.write_text("x = 1\ny = 2\n")
    await asyncio.sleep(1.5)

    watcher.stop()
    assert len(received) == 1
    assert "+ y = 2" in received[0].diff
    assert received[0].path == str(target)


@pytest.mark.asyncio
async def test_file_watcher_tracks_multiple_saves(tmp_path):
    target = tmp_path / "sol.py"
    target.write_text("pass\n")

    received: list[FileDelta] = []

    async def on_delta(delta: FileDelta):
        received.append(delta)

    watcher = FileWatcher(path=str(target), on_delta=on_delta)
    watcher.start()

    await asyncio.sleep(0.3)
    target.write_text("x = 1\n")
    await asyncio.sleep(1.2)
    target.write_text("x = 1\ny = 2\n")
    await asyncio.sleep(1.2)

    watcher.stop()
    assert len(received) == 2
