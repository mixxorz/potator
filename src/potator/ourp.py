""" Onion URL Resolution Protocol module. Handles all things OURP.
"""

import hashlib
import json
import time

from twisted.internet import task
from twisted.python import log

from .protocol.potator_pb2 import Spore, OurpData


class OnionUrlResolutionProtocol(object):
    """ Handles sending and receiving OURP messages.
    """

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
        """ Sends an OURP request broadcast for an IP address

        :param str ip_addrses: The IP address to query

        This method creates the OURP request packet, wraps it around a spore \
        and broadcasts it by calling \
        :func:`potator.network_dispatcher.NetworkDispatcher.handleDispatch`
        """
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.BROADCAST
        spore.hash = self._generateHash()
        spore.ourpData.type = OurpData.REQUEST
        spore.ourpData.ipAddress = self.potator.config['IP_ADDRESS']
        # TODO: There might be a more elegant way of doing this
        self.potator.network_dispatcher.handleDispatch(spore)

    def sendReply(self):
        """ Sends an OURP reply if a request for the Potator instance's IP \
        address is received

        This method creates the OURP reply packet, wraps it around a spore \
        and broadcasts it by calling \
        :func:`potator.network_dispatcher.NetworkDispatcher.handleDispatch`
        """
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
        """ Sends an OURP greeting to destination

        :param str destination: The onion URL to send the greeting to

        The OURP greeting packet is crafted and sent to the onion URL by \
        calling :func:`potator.tor.server.Server.sendSpore`.

        The OURP greeting is sent in a loop until Potator receives an OURP \
        greeting acknowledge.
        """
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
            log.msg('[OURP] GREETING to %s' % destination)
            self.potator.server.sendSpore(
                destination, spore.SerializeToString())
            self.potator.network_dispatcher.hash_cache.append(spore.hash)

        # Retry every 5 seconds
        l = task.LoopingCall(looper)
        l.start(5.0)
        self.greeting_loop = l

    def sendGreetingAck(self, destination):
        """ Sends an OURP greeting acknowledge to destination

        :param str destination: The onion URL to send the greeting acknowledge \
                                to
        """
        spore = Spore()
        spore.dataType = spore.OURP
        spore.castType = spore.UNICAST
        spore.ourpData.type = OurpData.GREETING_ACK
        spore.ourpData.ipAddress = self.potator.config['IP_ADDRESS']
        spore.ourpData.onionUrl = self.potator.server.tor_launcher.port.getHost(
        ).onion_uri
        self.potator.server.sendSpore(destination, spore.SerializeToString())

    def processOurp(self, ourpData):
        """ Responds to received OURP messages

        :param ourpData: The OURP data

        Different actions are done depending on the type of OURP message \
        received
        """
        if ourpData.type == OurpData.REQUEST:
            log.msg('Received OURP Request')

            if ourpData.ipAddress == self.potator.config['IP_ADDRESS']:
                self.sendReply()
        elif ourpData.type == OurpData.REPLY:
            log.msg('Received OURP Reply')

            self.potator.db.setOnionUrl(ourpData.ipAddress, ourpData.onionUrl)

        elif ourpData.type == OurpData.GREETING:
            log.msg('[OURP] GREETING from %s' % ourpData.onionUrl)
            # If password is set
            if self.potator.config.get('NETWORK_PASSWORD'):
                if not ourpData.payload:  # no payload, no reply
                    log.msg('[OURP] GREETING NO PAYLOAD')
                    return

                payload = json.loads(ourpData.payload)
                if not payload['password'] == self.potator.config['NETWORK_PASSWORD']:
                    log.msg('[OURP] GREETING WRONG PASSWORD')
                    return

                # Made it here, password correct
                log.msg('[OURP] GREETING AUTH SUCCESS')

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
