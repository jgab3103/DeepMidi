import asyncio
import logging
import json
import signal
from mido import Message
from .midi_io import MidiIO
from .db import DB
from .router import Router
from .model_stream import ModelStream
from .sc_osc import SCClient
from .utils import now_iso, now_ts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# configure ports here, or load from config.yaml
INPUT_PORTS = [
    "MC8Pro USB MIDI 1",    # replace with actual OS port names
    "Octatrack MIDI",
    "Modwave MIDI"
]
OUTPUT_PORTS = [
    "MC8Pro USB MIDI 1",
    "Octatrack MIDI",
    "Modwave MIDI"
]

async def midi_consumer_loop(event_q: asyncio.Queue, model: ModelStream, db: DB, router: Router, midi_io: MidiIO, sc_client: SCClient):
    # Start model generator
    model_gen = model.run()
    async def model_reader():
        async for generated in model_gen:
            # route generated to hardware & SC
            tgt_device = generated.get("target_device")
            out_port = router.get_output_port_for(tgt_device) or tgt_device
            if out_port and out_port in midi_io.out_ports:
                # construct mido message
                if generated["type"] == "note_on":
                    msg = Message('note_on', note=generated["note"], velocity=generated["velocity"], channel=generated.get("channel", 0))
                    midi_io.send(out_port, msg)
                elif generated["type"] == "control_change":
                    msg = Message('control_change', control=generated["control"], value=generated["value"], channel=generated.get("channel", 0))
                    midi_io.send(out_port, msg)
            # also send to SuperCollider if desired
            sc_client.send("/midi_gen", json.dumps(generated))

    reader_task = asyncio.create_task(model_reader())

    try:
        while True:
            parsed = await event_q.get()
            # push into model
            await model.push(parsed)
            # optionally forward some messages immediately (e.g., pass-through)
            # For this starter, do nothing here; the model will decide what to send back
    except asyncio.CancelledError:
        reader_task.cancel()
        raise

def start_midi_input_loop(event_q: asyncio.Queue, db: DB, router: Router):
    """
    Returns a callback function to be used by MidiIO for input callbacks.
    This callback runs in mido's background thread, so we must be careful:
    - put parsed event into asyncio queue (use loop.call_soon_threadsafe)
    - write to DB directly (sqlite is threadsafe under our config) or via loop to db queue
    """
    loop = asyncio.get_event_loop()
    def callback(msg, port_name):
        # parse msg
        try:
            # attempt to find logical device by port
            device_name, info = router.lookup_device_by_port(port_name, getattr(msg, "channel", None))
            if device_name is None:
                device_name = port_name  # fallback

            parsed = {
                "ts": now_ts(),
                "ts_iso": now_iso(),
                "src_port": port_name,
                "src_device": device_name,
                "type": msg.type,
                "channel": getattr(msg, "channel", None),
                "note": getattr(msg, "note", None),
                "velocity": getattr(msg, "velocity", None),
                "control": getattr(msg, "control", None),
                "value": getattr(msg, "value", None)
            }

            # 1) write to DB (synchronous but quick)
            db.insert_midi_event(port_name, device_name, getattr(msg, "channel", None), msg, parsed=parsed)

            # 2) enqueue for model processing in event loop
            loop.call_soon_threadsafe(asyncio.create_task, event_q.put(parsed))
        except Exception as e:
            logger.exception("Error in MIDI input callback: %s", e)

    return callback

async def main():
    db = DB()
    router = Router(db)
    model = ModelStream()
    sc_client = SCClient(host="127.0.0.1", port=57120)

    # Initialize MIDI IO
    midi_io = MidiIO(input_port_names=INPUT_PORTS, output_port_names=OUTPUT_PORTS)
    midi_io.open_outputs()

    # Async queue between MIDI thread and async world
    event_q = asyncio.Queue(maxsize=10000)

    # Start input ports with callback
    cb = start_midi_input_loop(event_q, db, router)
    midi_io.open_inputs(cb)

    # Start consumer loop
    consumer_task = asyncio.create_task(midi_consumer_loop(event_q, model, db, router, midi_io, sc_client))

    # Wait for termination signal
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    def _sig(*_):
        stop.set()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, _sig)

    await stop.wait()
    consumer_task.cancel()
    midi_io.close()
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
