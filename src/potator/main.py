import argparse
import random
import sys

from impacket import ImpactDecoder
from twisted.internet import reactor
from twisted.python import log

from .api import PotatorApiFactory
from .database import OnionIPMapper
from .network_dispatcher import NetworkDispatcher
from .ourp import OnionUrlResolutionProtocol
from .ping import PingProtocol
from .protocol.potator_pb2 import Spore
from .tor.server import Server
from .tuntap.tuntap import TunInterface


class Potator(object):

    def __init__(self, args):
        log.startLogging(sys.stdout)
        self.db = OnionIPMapper()

        # Store all configuration in this dictionary
        self.config = {
            'IP_ADDRESS': args.ip_address,
            'NETWORK_ID': args.network_identifier,
            'SOCKS_PORT': random.randint(49152, 65535),
            'API_PORT': random.randint(49152, 65535),
            'CONTROL_PORT': random.randint(49152, 65535),
            'HIDDEN_SERVICE_PORT': 7701
        }

        self.ourp = OnionUrlResolutionProtocol(self)
        self.network_dispatcher = NetworkDispatcher(self)
        self.ping = PingProtocol(self)

        self.server = Server(reactor, self)
        self.interface = TunInterface(self)
        # self.stats = StatPrinter(server, interface)

        reactor.listenTCP(self.config['API_PORT'], PotatorApiFactory(self))

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
        spore = self.network_dispatcher.handleDispatch(spore)

        if spore:
            # Packet Handler
            if spore.dataType == spore.OURP:
                self.ourp.processOurp(spore.ourpData)
            elif spore.dataType == spore.IP:
                decoder = ImpactDecoder.IPDecoder()
                packet = decoder.decode(spore.ipData.data)
                # Append to local interface buffer
                self.interface.writeBuffer.put(packet)
            elif spore.dataType == spore.PING:
                self.ping.processPing(spore.ping)

    def outgoingCallback(self, packet):
        # TODO: For testing only. Filtering out unwanted packets.
        # if '4.4.4' in packet.get_ip_dst():
        self.interface.sent_bytes += packet.get_size()

        spore = Spore()
        spore.dataType = spore.IP
        spore.castType = spore.UNICAST
        spore.ipData.destinationAddress = packet.get_ip_dst()
        spore.ipData.data = packet.get_packet()

        # TODO: Group number must not be static
        # TODO: Consider in memory database for better performance
        destination_onion_url = self.db.getOnionUrl(packet.get_ip_dst())

        if destination_onion_url:
            self.server.sendSpore(
                destination_onion_url, spore.SerializeToString())
        else:
            self.ourp.sendRequest(packet.get_ip_dst())


def main():
    parser = argparse.ArgumentParser(description='Potator v0.1')
    parser.add_argument(
        'ip_address',
        help='An IP address in CIDR notation (e.g. 4.4.4.1/8) to be used.')
    parser.add_argument(
        'network_identifier',
        help='A name for this Potator network.')

    app = Potator(parser.parse_args())

    reactor.addSystemEventTrigger('before', 'shutdown', app.stop)
    app.start()

if __name__ == '__main__':
    sys.exit(main())
