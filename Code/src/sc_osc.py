from pythonosc import udp_client
import logging

logger = logging.getLogger("sc_osc")

class SCClient:
    def __init__(self, host="127.0.0.1", port=57120):
        self.client = udp_client.SimpleUDPClient(host, port)

    def send(self, address, *args):
        try:
            self.client.send_message(address, list(args))
        except Exception as e:
            logger.exception("OSC send failed: %s", e)
