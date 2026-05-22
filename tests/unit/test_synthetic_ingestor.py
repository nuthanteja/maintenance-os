import asyncio

import pytest

from pmos.streaming.synthetic import SyntheticIngestor


@pytest.mark.asyncio
async def test_emits_axis_cycle():
    ingestor = SyntheticIngestor(window_period_s=0.001, seed=7)
    seen_axes: list[str] = []

    async def consume():
        async for event in ingestor.events():
            assert event.samples.shape == (1024,)
            assert event.axis in {"X", "Y", "Z"}
            seen_axes.append(event.axis)
            if len(seen_axes) >= 6:
                await ingestor.stop()

    await asyncio.wait_for(consume(), timeout=2.0)
    assert seen_axes[:3] == ["X", "Y", "Z"]
    assert seen_axes[3:6] == ["X", "Y", "Z"]
