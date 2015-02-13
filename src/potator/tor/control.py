import glob
import os

import txtorcon
from twisted.internet import reactor, defer
from twisted.python import log


class TorLauncher(object):

    def __init__(self, server):
        self.server = server
        self.port = None
        # Tor Configuration
        data_directory = os.path.join(
            'C:\\', 'potator',
            self.server.potator.config['NETWORK_ID'])
        try:
            os.mkdir(data_directory)
        except OSError:
            pass
        self.config = txtorcon.TorConfig()
        self.config.SocksPort = self.server.potator.config['SOCKS_PORT']
        self.config.ControlPort = self.server.potator.config['CONTROL_PORT']
        self.config.DataDirectory = data_directory

        # For testing tor network
        # TODO: This is only for testing, configure properly for production
        self.config.TestingTorNetwork = 1
        self.config.DirAuthority = [
            'test000a orport=5000 no-v2 hs v3ident=48BE4D5109DB962D54858309C7EECE4887C064B8 192.168.1.147:7000 B342E8AA94320304AC0C68658C3C0DEAE3286C7D',
            'test001a orport=5001 no-v2 hs v3ident=830F1E09AAC3A99948279F0A59C083F0AC39FF8F 192.168.1.147:7001 F5A783D42840CBDB9505BB05F3F4B8DF78206309',
            'test002a orport=5002 no-v2 hs v3ident=ABB238BF33AB89A65239F94E59A2908C26EB7C76 192.168.1.147:7002 15CB3AB45401452FE8F506FA2A0CC2516814D843'
        ]

        self.config.save()

        # TODO: REFRACTOR
        tor_binary = None
        globs = (
            'C:\\Program Files\\Tor\\',
            'C:\\Program Files (x86)\\Tor\\',
        )
        for pattern in globs:
            for path in glob.glob(pattern):
                torbin = os.path.join(path, 'tor.exe')
                if os.path.isfile(torbin) and os.access(torbin, os.X_OK):
                    tor_binary = torbin
                    break

        d = txtorcon.launch_tor(
            self.config,
            reactor,
            tor_binary=tor_binary,
            progress_updates=self.progress)
        d.addCallback(self.launched).addErrback(self.error)

    @defer.inlineCallbacks
    def launched(self, process_proto):
        log.msg("Tor has launched.")
        log.msg("SocksPort is on ", self.config.SocksPort)
        hidden_service_dir = os.path.join(
            self.config.DataDirectory, 'hidden_service')

        # Starts the listening server
        endpoint = txtorcon.TCPHiddenServiceEndpoint(
            reactor, self.config,
            self.server.potator.config['HIDDEN_SERVICE_PORT'],
            hidden_service_dir=hidden_service_dir)
        self.port = yield endpoint.listen(self.server.factory)

    def error(self, failure):
        log.msg("There was an error", failure.getErrorMessage())
        reactor.stop()

    def progress(self, percent, tag, summary):
        ticks = int((percent / 100.0) * 10.0)
        prog = (ticks * '#') + ((10 - ticks) * '.')
        log.msg('%s %s' % (prog, summary))
