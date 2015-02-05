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
            'test000a orport=5000 no-v2 hs v3ident=F8AB5EEF253B876DAC339FC5803FA41F57D8AE6B 192.168.64.133:7000 B980438D9E7F01698702C81C97290B73E6BE5064',
            'test001a orport=5001 no-v2 hs v3ident=C2FB9DF34B7A7D4D7AF4AB623D88E58374FC1B16 192.168.64.133:7001 C37CF77851F0F7D865F1F11841D543A9E52FFA0D',
            'test002a orport=5002 no-v2 hs v3ident=E51DBE6F08A2844A002816C59C619BAD7739BBCA 192.168.64.133:7002 E81679656CAFBA3C6B7EC9251017F459B74E03A0'
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
