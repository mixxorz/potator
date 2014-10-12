import sys
from collections import deque
from threading import Lock

from impacket import ImpactDecoder
from twisted.internet import reactor, threads
from twisted.python import log

from .api import PotatorApiFactory
from .database import Database
from .protocol.potator_pb2 import Spore, OurpData
from .stats import StatPrinter
from .tor.server import Server
from .tuntap.tuntap import TunInterface
from .util import settings


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


class OnionUrlResolutionProtocol(object):

    def __init__(self, potator):
        self.potator = potator

    def sendGreeting(self, destination):
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.BROADCAST
        spore.ourpData.type = OurpData.GREETING
        spore.ourpData.ipAddress = settings.IP_ADDRESS
        spore.ourpData.onionUrl = settings.ONION_URL
        self.potator.server.sendSpore(destination, spore.SerializeToString())

    def sendGreetingAck(self, destination):
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.UNICAST
        spore.ourpData.type = OurpData.GREETING_ACK
        spore.ourpData.ipAddress = settings.IP_ADDRESS
        spore.ourpData.onionUrl = settings.ONION_URL
        self.potator.server.sendSpore(destination, spore.SerializeToString())

    def processOurp(self, ourpData):
        if ourpData.type == OurpData.REQUEST:
            pass
        elif ourpData.type == OurpData.REPLY:
            pass
        elif ourpData.type == OurpData.GREETING:
            log.msg('Greeting received')
            log.msg(ourpData)
            # TODO: Check password and group ID
            # TODO: Don't just use '1' for group id
            # Save client's data
            self.potator.db.setOnionURL(
                ourpData.ipAddress, ourpData.onionUrl, 1)
            # Send greeting acknowledge
            self.sendGreetingAck(ourpData.onionUrl)

        elif ourpData.type == OurpData.GREETING_ACK:
            pass
        else:
            # Error
            pass


class Potator(object):

    def __init__(self):
        log.startLogging(sys.stdout)
        self.db = Database(Lock())
        self.ourp = OnionUrlResolutionProtocol(self)

        self.server = Server(reactor, self)
        self.interface = LocalInterface()
        # self.stats = StatPrinter(server, interface)

        # Tun adapter read/write buffer loop
        threads.deferToThread(self.sending_loop)

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
        # TODO: Add logic for network dispatcher

        # Packet Handler
        spore = Spore()
        spore.ParseFromString(spore_string)

        # TODO: Add OURP logic
        if spore.dataType == spore.OURP:
            self.ourp.processOurp(spore.ourpData)
        elif spore.dataType == spore.IP:
            decoder = ImpactDecoder.IPDecoder()
            packet = decoder.decode(spore.ipData.data)
            # Append to local interface buffer
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
