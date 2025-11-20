import json
from .db import DB

class Router:
    def __init__(self, db: DB):
        self.db = db
        # load device table into memory for fast lookup
        self._load_devices()

    def _load_devices(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT name, parent_device, midi_in_port, midi_out_port, default_channel, notes FROM devices")
        self.devices = {}
        for row in cur.fetchall():
            name, parent, inport, outport, default_channel, notes = row
            self.devices[name] = {
                "parent": parent,
                "midi_in_port": inport,
                "midi_out_port": outport,
                "default_channel": default_channel,
                "notes": json.loads(notes) if notes else {}
            }

    def lookup_device_by_port(self, port_name, channel=None):
        # Best-effort guess: find device with matching midi_in_port or parent mapping.
        for name, info in self.devices.items():
            if info.get("midi_in_port") == port_name:
                return name, info
        return None, None

    def get_output_port_for(self, device_name):
        info = self.devices.get(device_name)
        if info:
            return info.get("midi_out_port")
        return None
