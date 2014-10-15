import sys
from threading import Lock

from impacket import ImpactDecoder
from twisted.internet import reactor
from twisted.python import log

from .api import PotatorApiFactory
from .database import Database
from .network_dispatcher import NetworkDispatcher
from .ourp import OnionUrlResolutionProtocol
from .protocol.potator_pb2 import Spore
from .tor.server import Server
from .tuntap.tuntap import TunInterface


class Potator(object):

    def __init__(self):
        log.startLogging(sys.stdout)
        self.db = Database(Lock())
        # Purge database at start to test. OURP + database
        self.db.dropdb()
        self.db.syncdb()

        self.ourp = OnionUrlResolutionProtocol(self)
        self.network_dispatcher = NetworkDispatcher(self)

        self.server = Server(reactor, self)
        self.interface = TunInterface(self)
        # self.stats = StatPrinter(server, interface)

        reactor.listenTCP(9999, PotatorApiFactory(self))

    def start(self):
        self.interface.start()
        # self.stats.start()
        reactor.run()

    def stop(self):
        self.interface.stop()
        # self.stats.stop()
        reactor.stop()

    def incomingCallback(self, spore_string):
        spore = Spore()
        spore.ParseFromString(spore_string)
        # TODO: Add logic for network dispatcher
        self.network_dispatcher.handleDispatch(spore)

        # Packet Handler

        # TODO: Add OURP logic
        if spore.dataType == spore.OURP:
            self.ourp.processOurp(spore.ourpData)
        elif spore.dataType == spore.IP:
            decoder = ImpactDecoder.IPDecoder()
            packet = decoder.decode(spore.ipData.data)
            # Append to local interface buffer
            self.interface.send_buffer.append(packet)

    def outgoingCallback(self, packet):
        # TODO: For testing only. Filtering out unwanted packets.
        if '4.4.4' in packet.get_ip_dst():
            self.interface.sent_bytes += packet.get_size()

            spore = Spore()
            spore.dataType = spore.IP
            spore.castType = spore.UNICAST
            spore.ipData.destinationAddress = packet.get_ip_dst()
            spore.ipData.data = packet.get_packet()

            # TODO: Group number must not be static
            # TODO: Consider in memory database for better performance
            destination_onion_url = self.db.getOnionUrl(
                packet.get_ip_dst(),
                1
            )

            if destination_onion_url:
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
