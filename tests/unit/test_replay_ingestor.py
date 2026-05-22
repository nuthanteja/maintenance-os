import asyncio
import json
from pathlib import Path

import numpy as np
import pytest

from pmos.streaming.replay import JsonlReplayIngestor


def _write_replay(path: Path, n_triplets: int = 3) -> None:
    rng = np.random.default_rng(42)
    lines = []
    t = 1.0
    for _ in range(n_triplets):
        for axis in ("X", "Y", "Z"):
            lines.append(
                json.dumps(
                    {"time": t, "axis": axis, "data": rng.standard_normal(1024).tolist()}
                )
            )
            t += 0.02
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_replays_records_in_order(tmp_path):
    p = tmp_path / "r.jsonl"
    _write_replay(p, n_triplets=2)

    ingestor = JsonlReplayIngestor(p, realtime=False, loop=False)
    seen_axes: list[str] = []

    async for event in ingestor.events():
        seen_axes.append(event.axis)

    assert seen_axes == ["X", "Y", "Z", "X", "Y", "Z"]


@pytest.mark.asyncio
async def test_loop_mode_keeps_emitting(tmp_path):
    p = tmp_path / "r.jsonl"
    _write_replay(p, n_triplets=1)

    ingestor = JsonlReplayIngestor(p, realtime=False, loop=True)
    count = 0

    async def consume():
        nonlocal count
        async for _ in ingestor.events():
            count += 1
            if count >= 9:
                await ingestor.stop()

    await asyncio.wait_for(consume(), timeout=2.0)
    assert count >= 9


@pytest.mark.asyncio
async def test_missing_file_raises(tmp_path):
    ingestor = JsonlReplayIngestor(tmp_path / "nope.jsonl", realtime=False, loop=False)
    with pytest.raises(FileNotFoundError):
        async for _ in ingestor.events():
            pass
