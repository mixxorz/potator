from twisted.internet import reactor
from twisted.python import log

from .protocol.potator_pb2 import Spore


class NetworkDispatcher(object):

    def __init__(self, potator):
        self.potator = potator
        self.hash_cache = []
        self.timeout = 60

        # Clear every 60 seconds
        reactor.callLater(self.timeout, self._clearHashStore)

    def _clearHashStore(self):
        log.msg('Clearing hash store')
        self.hash_cache = []
        reactor.callLater(self.timeout, self._clearHashStore)

    def _broadcast(self, data, group_id, exclude=None):
        nodes = [x for x in self.potator.db.getAllOnionUrls(group_id)]

        if exclude:
            nodes.remove(exclude)

        for node in nodes:
            self.potator.server.sendSpore(node, data)

    def handleDispatch(self, spore):
        ''' handles dispatching of broadcast spores

        returns the spore object. If returns none, it means the packet should be dropped
        '''
        if spore.castType == Spore.BROADCAST and spore.dataType == Spore.OURP:
            if not spore.hash in self.hash_cache:
                # TODO: Group ID should not just be '1'
                self._broadcast(spore.SerializeToString(), 1)
                self.hash_cache.append(spore.hash)
                log.msg('Hash stored: %s' % spore.hash)
                return spore
        return None
