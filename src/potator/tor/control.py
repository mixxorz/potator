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
            'test000a orport=5000 no-v2 hs v3ident=39AF0AA2DCA0A1618C0D803EB3EC22090CD644F8 172.16.4.60:7000 293A7EB55F586E40FB541D299798EC599D2E9482',
            'test001a orport=5001 no-v2 hs v3ident=7310E052432DC607537F53518BC819910EF8E4E7 172.16.4.60:7001 33A25398A02D4566AFFC737918DC5ADE1B0CCFDA',
            'test002a orport=5002 no-v2 hs v3ident=1D4073AE0D1B7C978302F819504176F5D06259DA 172.16.4.60:7002 DC7A790EB84313F923D26754CE355BDF9E093EC9'
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
