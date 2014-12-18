from twisted.internet import defer
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.protocol import Factory
from twisted.protocols.basic import NetstringReceiver
from twisted.python import log
from txsocksx.client import SOCKS5ClientEndpoint

from .control import TorLauncher


class NodeConnection(NetstringReceiver):

    def connectionLost(self, reason):
        # Remove node from node list if connection is lost
        pair = next((x for x in self.factory.nodes if x[1] is self), None)
        if pair:
            log.msg('Removing %s' % pair[0])
            self.factory.nodes.remove(pair)

    def stringReceived(self, string):
        self.factory.server.potator.incomingCallback(string)


class NodeFactory(Factory):

    def __init__(self, server):
        self.nodes = []
        self.server = server

    def buildProtocol(self, addr):
        protocol = NodeConnection()
        protocol.factory = self
        return protocol


class Server(object):

    # TODO: Remove reactor
    def __init__(self, reactor, potator):
        self.reactor = reactor
        self.potator = potator

        # Create the factory
        self.factory = NodeFactory(self)

        # Starts Tor and the listening server
        self.tor_launcher = TorLauncher(self)

    def sendSpore(self, onion_url, spore):
        log.msg('Sending to %s' % onion_url)
        d = self.getProtocol(onion_url)
        d.addCallback(self.send, spore)

    def send(self, protocol, data):
        protocol.sendString(data)

    def getProtocol(self, onion_url):
        protocol = next(
            (x[1]
             for x in self.factory.nodes if x[0] == onion_url),
            None
        )

        # If it's found, just use that
        if protocol:
            # Pass to next callback
            d = defer.Deferred()
            d.callback(protocol)
            return d
        # If not, make a connection
        else:
            d = self.connectTorSocks(onion_url)
            d.addCallback(self.registerNode, onion_url)
            return d

    def ignore_error(self, err):
        pass

    def registerNode(self, protocol, onion_url):
        log.msg('Register %s' % onion_url)
        self.factory.nodes.append((onion_url, protocol,))
        return protocol

    def connectTorSocks(self, host):
        # Host must be str, not unicode
        if type(host) == unicode:
            host = host.encode('utf-8')

        tcp_endpoint = TCP4ClientEndpoint(
            self.reactor, '127.0.0.1', self.potator.config['SOCKS_PORT'])

        endpoint = SOCKS5ClientEndpoint(
            host, self.potator.config['HIDDEN_SERVICE_PORT'], tcp_endpoint)

        d = endpoint.connect(self.factory)
        return d
