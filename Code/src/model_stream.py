import asyncio
import logging
from typing import AsyncGenerator

logger = logging.getLogger("model_stream")

class ModelStream:
    """
    Example streaming interface.
    Replace the internals with your real model (Torch/RL/TF).
    The model receives parsed midi messages and yields generated midi messages.
    """

    def __init__(self):
        self._queue = asyncio.Queue()

    async def push(self, parsed_msg):
        await self._queue.put(parsed_msg)

    async def run(self) -> AsyncGenerator[dict, None]:
        """
        Async generator that yields model-produced actions.
        This stub echos back messages with small modification as example.
        """
        while True:
            parsed = await self._queue.get()
            # Simulate computation latency small non-blocking sleep (replace with real async inference)
            await asyncio.sleep(0.001)
            # Example: echo note-on as velocity-halved note on channel+1
            out = None
            if parsed.get("type") == "note_on":
                out = {
                    "type": "note_on",
                    "note": parsed.get("note"),
                    "velocity": max(1, parsed.get("velocity", 64)//2),
                    "channel": (parsed.get("channel", 0) + 1) % 16,
                    "target_device": parsed.get("src_device")  # you might route elsewhere
                }
            elif parsed.get("type") == "control_change":
                out = {
                    "type": "control_change",
                    "control": parsed.get("control"),
                    "value": parsed.get("value"),
                    "channel": parsed.get("channel", 0),
                    "target_device": parsed.get("src_device")
                }

            if out:
                yield out
