""" Potator's main controller
"""
import argparse
import json
import os
import random
import sys

import ipaddr
from impacket import ImpactDecoder
from twisted.internet import reactor
from twisted.python import log
from twisted.web import server

from .api import PotatorAPI
from .database import OnionIPMapper
from .network_dispatcher import NetworkDispatcher
from .ourp import OnionUrlResolutionProtocol
from .ping import PingProtocol
from .protocol.potator_pb2 import Spore
from .tor.server import Server
from .tuntap.tuntap import TunInterface


class Potator(object):
    """ The main controller. Coordinates between all the modules.
    """

    def __init__(self, args):
        log.startLogging(sys.stdout)
        self.db = OnionIPMapper()

        if not os.path.exists('C:\\potator'):
            os.makedirs('C:\\potator')

        # Store all configuration in this dictionary
        self.config = {
            'NETWORK_ID': args.network_identifier,
            'NETWORK_PASSWORD': args.password,
            'SOCKS_PORT': random.randint(49152, 65535),
            'API_PORT': random.randint(49152, 65535),
            'CONTROL_PORT': random.randint(49152, 65535),
            'HIDDEN_SERVICE_PORT': 7701
        }

        # Save config
        if args.new:
            config_path = os.path.join(
                'C:\\potator', args.network_identifier)
            if not os.path.exists(config_path):
                os.makedirs(config_path)
            config_file = open(os.path.join(config_path, 'config.json'), 'w+')
            configuration = {
                'network_identifier': args.network_identifier,
                'ip_network': args.ip_network
            }
            if args.password:
                configuration['password'] = args.password

            config_file.write(json.dumps(configuration, indent=2))
            ip = ipaddr.IPv4Network(args.ip_network)
            self.config['IP_ADDRESS'] = str(ip.ip)
            self.config['IP_NETWORK'] = args.ip_network
            config_file.close()
            log.msg('Network %s created.' % self.config['NETWORK_ID'])
            log.msg('You can now use this network by running `python cli.py %s`' %
                    self.config['NETWORK_ID'])
            sys.exit(0)

        # Load config if new flag is not set
        else:
            config_file = open(
                os.path.join('C:\\potator', args.network_identifier, 'config.json'))
            configuration = json.load(config_file)
            self.config['IP_NETWORK'] = configuration['ip_network']
            self.config['IP_ADDRESS'] = str(
                ipaddr.IPv4Network(configuration['ip_network']).ip)
            self.config['NETWORK_ID'] = configuration['network_identifier']
            self.config['NETWORK_PASSWORD'] = configuration.get(
                'password', None)

            config_file.close()

        self.ourp = OnionUrlResolutionProtocol(self)
        self.network_dispatcher = NetworkDispatcher(self)
        self.ping = PingProtocol(self)

        self.server = Server(reactor, self)
        self.interface = TunInterface(self)
        # self.stats = StatPrinter(server, interface)

        reactor.listenTCP(self.config['API_PORT'],
                          server.Site(PotatorAPI(self)))

    def start(self):
        """ Starts Potator
        """
        # self.interface.start()
        # self.stats.start()
        reactor.run()

    def stop(self):
        """ Stops Potator, initiates cleanup
        """
        self.interface.stop()
        # self.stats.stop()
        # reactor.stop()

    def incomingCallback(self, spore_string):
        """ Callback when a spore is received from a remote node

        :param str spore_string: The spore encoded string

        The :code:`spore` is decoded from the :code:`spore_string` using \
        protobuf. :code:`spore` is then passed into \
        :func:`potator.network_dispatcher.NetworkDispatcher.handleDispatch`.

        Depending on whether the spore contains IP or OURP data, it will then \
        be passed into the OURP module or Tuntap module.
        """
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
        """ Callback when an outgoing IP packet is received from Tuntap

        :param packet: The IP packet

        The packet is loaded into a Spore object and encoded into a string \
        using protobuf. The destination onion URL is acquired from \
        :func:`potator.database.OnionIPMapper.getOnionUrl`. If the destination \
        onion URL is not found for the IP address, an OURP request is sent by \
        calling :func:`potator.ourp.OnionUrlResolutionProtocol.sendRequest`. \
        If the destination is found, the spore encoded string is sent to its \
        destination by calling :func:`potator.tor.server.Server.sendSpore`.
        """
        self.interface.sent_bytes += packet.get_size()

        spore = Spore()
        spore.dataType = spore.IP
        spore.castType = spore.UNICAST
        spore.ipData.destinationAddress = packet.get_ip_dst()
        spore.ipData.data = packet.get_packet()

        destination_onion_url = self.db.getOnionUrl(packet.get_ip_dst())

        if destination_onion_url:
            self.server.sendSpore(
                destination_onion_url, spore.SerializeToString())
        else:
            self.ourp.sendRequest(packet.get_ip_dst())


def main():
    """ The main method. Passes arguments, creates an instance of \
    :class:`.Potator`.
    """
    parser = argparse.ArgumentParser(description='Potator v0.1')
    parser.add_argument(
        'network_identifier',
        help='A name for this Potator network.')
    parser.add_argument(
        'ip_network',
        nargs='?',
        help='An IP address in CIDR notation (e.g. 4.4.4.1/8) to be used. e.g. 4.4.4.1/8 for 4.4.4.1 255.0.0.0.')
    parser.add_argument(
        '-p', '--password', nargs='?', const=None,
        help='Password for this network.')
    parser.add_argument(
        '-n', '--new', action='store_true', help='Saves this network.')

    app = Potator(parser.parse_args())

    reactor.addSystemEventTrigger('before', 'shutdown', app.stop)
    app.start()

if __name__ == '__main__':
    sys.exit(main())
