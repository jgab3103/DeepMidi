import mido
from mido import Message
import asyncio
import logging

logger = logging.getLogger("midi_io")

class MidiIO:
    def __init__(self, input_port_names=None, output_port_names=None):
        self.input_port_names = input_port_names or []
        self.output_port_names = output_port_names or []
        self.in_ports = {}
        self.out_ports = {}

    def open_outputs(self):
        for name in self.output_port_names:
            try:
                outp = mido.open_output(name)
                self.out_ports[name] = outp
                logger.info(f"Opened MIDI OUT {name}")
            except Exception as e:
                logger.exception(f"Failed to open out port {name}: {e}")

    def open_inputs(self, callback):
        # callback takes (msg, port_name)
        for name in self.input_port_names:
            try:
                port = mido.open_input(name, callback=lambda msg, pname=name: callback(msg, pname))
                self.in_ports[name] = port
                logger.info(f"Opened MIDI IN {name}")
            except Exception as e:
                logger.exception(f"Failed to open in port {name}: {e}")

    def send(self, port_name, msg):
        outp = self.out_ports.get(port_name)
        if outp:
            outp.send(msg)
        else:
            logger.warning(f"Output port {port_name} not open; cannot send {msg}")

    def close(self):
        for p in list(self.in_ports.values()) + list(self.out_ports.values()):
            try:
                p.close()
            except:
                pass
