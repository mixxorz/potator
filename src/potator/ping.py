""" Utility module that can send an internal ping between Potator nodes
"""

import time

from twisted.internet import reactor
from twisted.python import log

from .protocol.potator_pb2 import Spore


class PingProtocol(object):

    """ Handles received pings, and provides an API for sending pings.
    """

    def __init__(self, potator):
        self.potator = potator
        self.waiting = False
        self.time_buffer = None

    def ping(self, destination, count=4):
        """ Sends a ping to destination

        :param str destination: The onion URL to send the ping to
        :param int count: default 4, The number of pings to send.

        This methods sends a ping to :code:`destination` :code:`count` number \
        of times in 1 second intervals.
        """
        for x in range(1, count + 1):
            reactor.callLater(x, self.sendPing, destination)

    def sendPing(self, destination, reply=False):
        """ Sends a single ping to destination

        :param str destination: The onion URL to send the ping to
        :param bool reply: Whether this ping is a reply ping
        """
        spore = Spore()
        spore.dataType = spore.PING
        spore.castType = spore.UNICAST
        spore.ping.data = 'abcdefghijklmnopqrstuvwxyz1234567890'
        spore.ping.reply = reply
        spore.ping.source = self.potator.server.tor_launcher.port.getHost(
        ).onion_uri
        self.waiting = True
        self.time_buffer = time.time()
        self.potator.server.sendSpore(destination, spore.SerializeToString())

    def processPing(self, ping):
        """ Receives pings and logs their roundtrip time

        :param ping: The ping
        """
        now = time.time()
        if ping.reply and self.waiting:
            log.msg('PING: %s' % (now - self.time_buffer))
        else:
            log.msg('Sending reply to %s' % ping.source)
            self.sendPing(ping.source, True)

        self.waiting = False
