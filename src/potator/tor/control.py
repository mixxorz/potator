import glob
import json
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

        # Load custom config if it exists
        # We use this to connect to local tor networks
        try:
            with open(os.path.join('C:\\potator', 'torconfig.json'),
                      'r') as torconfigfile:
                log.msg('Loading custom tor configuration')
                torconfig = json.loads(torconfigfile.read())
                for key, value in torconfig.iteritems():
                    setattr(self.config, key, value)
        except IOError:
            pass

        self.config.save()

        # TODO: REFACTOR
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

        self.server.potator.db.setOnionUrl(
            self.server.potator.config['IP_ADDRESS'],
            self.port.getHost().onion_uri)

    def error(self, failure):
        log.msg("There was an error", failure.getErrorMessage())
        reactor.stop()

    def progress(self, percent, tag, summary):
        ticks = int((percent / 100.0) * 10.0)
        prog = (ticks * '#') + ((10 - ticks) * '.')
        log.msg('%s %s' % (prog, summary))
