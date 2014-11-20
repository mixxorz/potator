import time

from twisted.python import log

from .protocol.potator_pb2 import Spore
from .util import settings


class PingProtocol(object):

    def __init__(self):
        self.waiting = False
        self.time_buffer = None

    def sendPing(self, destination, reply=False):
        spore = Spore()
        spore.dataType = spore.PING
        spore.castType = spore.UNICAST
        spore.ping.data = 'abcdefghijklmnopqrstuvwxyz1234567890'
        spore.ping.reply = reply
        spore.ping.source = settings.ONION_URL
        self.waiting = True
        self.time_buffer = time.time()
        log.msg('sending...')
        log.msg(destination)
        log.msg(spore)
        log.msg(spore.SerializeToString())
        self.potator.server.sendSpore(destination, spore.SerializeToString())

    def processPing(self, ping):
        now = time.time()
        if ping.reply and self.waiting:
            log.msg('PING: %s' % (now - self.time_buffer))
        else:
            log.msg('Sending reply to %s' % ping.source)
            self.sendPing(ping.source, True)

        self.waiting = False
