import hashlib
import json
import time

from twisted.internet import task
from twisted.python import log

from .protocol.potator_pb2 import Spore, OurpData


class OnionUrlResolutionProtocol(object):

    def __init__(self, potator):
        self.potator = potator
        self.time_greeting_sent = None
        self.time_greeting_ack_laps = []
        self.greeting_loop = None

    def _generateHash(self):
        return hashlib.sha1(
            '%s%s' % (time.time(), self.potator.config['IP_ADDRESS'])
        ).hexdigest()

    def sendRequest(self, ip_address):
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.BROADCAST
        spore.hash = self._generateHash()
        spore.ourpData.type = OurpData.REQUEST
        spore.ourpData.ipAddress = self.potator.config['IP_ADDRESS']
        # TODO: There might be a more elegant way of doing this
        self.potator.network_dispatcher.handleDispatch(spore)

    def sendReply(self):
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.BROADCAST
        spore.hash = self._generateHash()
        spore.ourpData.type = OurpData.REPLY
        spore.ourpData.ipAddress = self.potator.config['IP_ADDRESS']
        spore.ourpData.onionUrl = self.potator.server.tor_launcher.port.getHost(
        ).onion_uri
        # TODO: There might be a more elegant way of doing this
        self.potator.network_dispatcher.handleDispatch(spore)

    def sendGreeting(self, destination):
        self.time_greeting_sent = time.time()
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.BROADCAST
        spore.hash = self._generateHash()
        spore.ourpData.type = OurpData.GREETING
        spore.ourpData.ipAddress = self.potator.config['IP_ADDRESS']
        spore.ourpData.onionUrl = self.potator.server.tor_launcher.port.getHost(
        ).onion_uri

        if self.potator.config.get('NETWORK_PASSWORD'):
            payload = {
                'password': self.potator.config.get('NETWORK_PASSWORD')
            }
            spore.ourpData.payload = json.dumps(payload)

        def looper():
            # Generate new hash every retry
            spore.hash = self._generateHash()
            self.potator.server.sendSpore(
                destination, spore.SerializeToString())
            self.potator.network_dispatcher.hash_cache.append(spore.hash)

        # Retry every 5 seconds
        l = task.LoopingCall(looper)
        l.start(5.0)
        self.greeting_loop = l

    def sendGreetingAck(self, destination):
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.UNICAST
        spore.ourpData.type = OurpData.GREETING_ACK
        spore.ourpData.ipAddress = self.potator.config['IP_ADDRESS']
        spore.ourpData.onionUrl = self.potator.server.tor_launcher.port.getHost(
        ).onion_uri
        self.potator.server.sendSpore(destination, spore.SerializeToString())

    def processOurp(self, ourpData):
        if ourpData.type == OurpData.REQUEST:
            log.msg('Received OURP Request')

            if ourpData.ipAddress == self.potator.config['IP_ADDRESS']:
                self.sendReply()
        elif ourpData.type == OurpData.REPLY:
            log.msg('Received OURP Reply')

            self.potator.db.setOnionUrl(ourpData.ipAddress, ourpData.onionUrl)

        elif ourpData.type == OurpData.GREETING:
            log.msg('Received OURP Greeting')
            # TODO: Check password
            if ourpData.payload:
                payload = json.loads(ourpData.payload)
                if not payload['password'] == self.potator.config['NETWORK_PASSWORD']:
                    return
            # Save client's data
            self.potator.db.setOnionUrl(ourpData.ipAddress, ourpData.onionUrl)
            # Send greeting acknowledge
            self.sendGreetingAck(ourpData.onionUrl)

        elif ourpData.type == OurpData.GREETING_ACK:
            now = time.time()
            log.msg('Received OURP Greeting Acknowledge')
            if self.time_greeting_sent:
                log.msg('ACK LAP: %s' % (now - self.time_greeting_sent))
            self.time_greeting_ack_laps.append(now)
            self.potator.db.setOnionUrl(ourpData.ipAddress, ourpData.onionUrl)

            # Stop the looping call
            if self.greeting_loop:
                self.greeting_loop.stop()
                self.greeting_loop = None
        else:
            # Error
            pass
