import hashlib
import time

from twisted.python import log

from .protocol.potator_pb2 import Spore, OurpData
from .util import settings


class OnionUrlResolutionProtocol(object):

    def __init__(self, potator):
        self.potator = potator

    def _generateHash(self):
        return str(hashlib.sha1('%s%s' % (time.time(), settings.IP_ADDRESS)))

    def sendGreeting(self, destination):
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.BROADCAST
        spore.hash = self._generateHash()
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
            # TODO: Check password and group ID
            # TODO: Don't just use '1' for group id
            # Save client's data
            self.potator.db.setOnionURL(
                ourpData.ipAddress, ourpData.onionUrl, 1)
            # Send greeting acknowledge
            self.sendGreetingAck(ourpData.onionUrl)

        elif ourpData.type == OurpData.GREETING_ACK:
            self.potator.db.setOnionURL(
                ourpData.ipAddress, ourpData.onionUrl, 1)
        else:
            # Error
            pass
