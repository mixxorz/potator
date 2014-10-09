from collections import deque

from potator.util import settings
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.protocol import Factory
from twisted.protocols.basic import NetstringReceiver
from txsocksx.client import SOCKS5ClientEndpoint


class NodeConnection(NetstringReceiver):

    def connectionLost(self, reason):
        # Remove node from node list if connection is lost
        pair = next((x for x in self.factory.nodes if x[1] is self), None)
        if pair:
            print 'Removing %s' % pair[0]
            self.factory.nodes.remove(pair)

    def stringReceived(self, string):
        self.factory.server.receive_buffer.append(string)


class NodeFactory(Factory):

    def __init__(self, server):
        self.nodes = []
        self.server = server

    def buildProtocol(self, addr):
        protocol = NodeConnection()
        protocol.factory = self
        return protocol


class Server(object):

    def __init__(self, reactor):

        self.endpoint = TCP4ClientEndpoint(
            reactor, '127.0.0.1', settings.SOCKS_PORT)

        self.receive_buffer = deque()
        self.send_buffer = deque()

        # Create the factory
        self.factory = NodeFactory(self)

        # Starts the listening server
        reactor.listenTCP(settings.SERVER_PORT, self.factory)

    def print_err(self, err):
        pass
        # print err

    def connectionFailure(self, err):
        return err

    def sendSpore(self, destination_onion_url, spore_string):
        protocol = next(
            (x[1]
             for x in self.factory.nodes if x[0] == destination_onion_url),
            None
        )

        # If it's found, just use that
        if protocol:
            protocol.sendString(spore_string)
        # If not, make a connection
        else:
            d = self.connectTorSocks(destination_onion_url, self.factory)
            d.addCallback(
                self.registerNode, self.factory, destination_onion_url)
            d.addCallback(self.sendSpore, spore_string)
            d.addErrback(self.print_err)

        return protocol

    def registerNode(self, protocol, factory, onion_url):
        print 'Register %s' % onion_url
        factory.nodes.append((onion_url, protocol,))
        return protocol

    def connectTorSocks(self, host, factory):
        # Host must be str, not unicode
        if type(host) == unicode:
            host = host.encode('utf-8')

        endpoint = SOCKS5ClientEndpoint(
            host, settings.HIDDEN_SERVICE_PORT, self.endpoint)

        d = endpoint.connect(factory)
        d.addErrback(self.connectionFailure)
        return d
