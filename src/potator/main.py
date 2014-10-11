import sys
from collections import deque

from twisted.internet import reactor, threads
from impacket import ImpactDecoder

from tor.server import Server
from tuntap.tuntap import TunInterface
from protocol.potator_pb2 import Spore
from .util import settings
from .stats import StatPrinter


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


def sending_loop(server, interface):
    while True:
        if interface.receive_buffer:
            packet = interface.receive_buffer.popleft()

            if '4.4.4' in packet.get_ip_dst():
                interface.sent_bytes += packet.get_size()

                spore = Spore()
                spore.dataType = spore.IP
                spore.castType = spore.UNICAST
                spore.ipData.destinationAddress = packet.get_ip_dst()
                spore.ipData.data = packet.get_packet()

                destination_onion_url = settings.DESTINATION

                server.sendSpore(
                    destination_onion_url, spore.SerializeToString())


def receiving_loop(server, interface):
    while True:
        if server.receive_buffer:
            spore_string = server.receive_buffer.popleft()
            spore = Spore()
            spore.ParseFromString(spore_string)

            decoder = ImpactDecoder.IPDecoder()
            packet = decoder.decode(spore.ipData.data)
            interface.send_buffer.append(packet)


def main():
    server = Server(reactor)
    interface = LocalInterface()
    interface.start()
    stats = StatPrinter(server, interface)
    stats.start()

    # To Tor thread
    threads.deferToThread(sending_loop, server, interface)

    # To Local thread
    threads.deferToThread(receiving_loop, server, interface)

    try:
        reactor.run()
    except KeyboardInterrupt:
        print 'Stopping...'
        reactor.stop()
        return 0


if __name__ == '__main__':
    sys.exit(main())
