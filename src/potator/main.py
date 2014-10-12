import sys
from collections import deque
from threading import Lock

from impacket import ImpactDecoder
from twisted.internet import reactor, threads
from twisted.python import log

from .database import Database
from .protocol.potator_pb2 import Spore, OurpData
from .stats import StatPrinter
from .tor.server import Server
from .tuntap.tuntap import TunInterface


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
        log.startLogging(sys.stdout)
        self.db = Database(Lock())

        self.server = Server(reactor, self)
        self.interface = LocalInterface()
        # self.stats = StatPrinter(server, interface)

        # Tun adapter read/write buffer loop
        threads.deferToThread(self.sending_loop)

    def start(self):
        self.interface.start()
        # self.stats.start()
        reactor.run()

    def stop(self):
        self.interface.stop()
        # self.stats.stop()
        reactor.stop()

    def incomingCallback(self, spore_string):
        # TODO: Add logic for network dispatcher

        # Packet Handler
        spore = Spore()
        spore.ParseFromString(spore_string)

        # TODO: Add OURP logic
        if spore.dataType == spore.OURP:
            self.processOurp(spore.ourpData)
        elif spore.dataType == spore.IP:
            decoder = ImpactDecoder.IPDecoder()
            packet = decoder.decode(spore.ipData.data)
            # Append to local interface buffer
            self.interface.send_buffer.append(packet)

    def processOurp(self, ourpData):
        if ourpData.type == OurpData.REQUEST:
            pass
        elif ourpData.type == OurpData.REPLY:
            pass
        elif ourpData.type == OurpData.GREETING:
            pass
        elif ourpData.type == OurpData.GREETING_ACK:
            pass
        else:
            # Error
            pass

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
                    destination_onion_url = self.db.getOnionURL(
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
