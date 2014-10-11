import sys
from collections import deque
from threading import Lock

from impacket import ImpactDecoder
from twisted.internet import reactor, threads

from .database import Database
from .protocol.potator_pb2 import Spore
from .stats import StatPrinter
from .tor.server import Server
from .tuntap.tuntap import TunInterface
from .view import CommandInput


_DAO = None


class LocalInterface(TunInterface):

    def __init__(self):
        self.sent_bytes = 0
        self.received_bytes = 0
        self.receive_buffer = deque()
        self.send_buffer = deque()
        TunInterface.__init__(self)

    def packetReceived(self, data):
        self.receive_buffer.append(data)

    def write(self, data):
        self.transmitter.transmit(data)


class Potator(object):

    def __init__(self):
        global _DAO
        _DAO = Database(Lock())

        self.server = Server(reactor)
        self.interface = LocalInterface()
        # self.stats = StatPrinter(server, interface)
        self.cmd = CommandInput()

        # To Tor thread
        threads.deferToThread(self.sending_loop)

        # To Local thread
        threads.deferToThread(self.receiving_loop)

    def start(self):
        self.interface.start()
        self.cmd.start()
        # self.stats.start()
        reactor.run()

    def stop(self):
        self.interface.stop()
        self.cmd.stop()
        # self.stats.stop()
        reactor.stop()

    def receiving_loop(self):
        while True:
            if self.server.receive_buffer:
                spore_string = self.server.receive_buffer.popleft()
                spore = Spore()
                spore.ParseFromString(spore_string)

                decoder = ImpactDecoder.IPDecoder()
                packet = decoder.decode(spore.ipData.data)
                self.interface.send_buffer.append(packet)

    def sending_loop(self):
        while True:
            if self.interface.receive_buffer:
                packet = self.interface.receive_buffer.popleft()

                if '4.4.4' in packet.get_ip_dst():
                    self.interface.sent_bytes += packet.get_size()

                    spore = Spore()
                    spore.dataType = spore.IP
                    spore.castType = spore.UNICAST
                    spore.ipData.destinationAddress = packet.get_ip_dst()
                    spore.ipData.data = packet.get_packet()

                    # TODO: Group number must not be static
                    # TODO: Consider in memory database for better performance
                    destination_onion_url = _DAO.getOnionURL(
                        packet.get_ip_dst(),
                        1
                    )

                    self.server.sendSpore(
                        destination_onion_url, spore.SerializeToString())


def main():
    app = Potator()

    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()
        return 0

if __name__ == '__main__':
    sys.exit(main())
