import os

import txtorcon
from twisted.internet import reactor, defer
from twisted.python import log


class TorLauncher(object):

    def __init__(self, factory):
        self.factory = factory
        self.port = None
        # Tor Configuration
        # TODO: This is only for testing, configure properly for production
        data_directory = os.path.join(os.environ['AppData'], 'potator', '0000')
        self.config = txtorcon.TorConfig()
        self.config.SocksPort = 7700
        self.config.DataDirectory = data_directory

        # For testing tor network
        self.config.TestingTorNetwork = 1
        self.config.DirAuthority = [
            'test000a orport=5000 no-v2 hs v3ident=45A84EC741477462D3189B79C5B8A086683CDD71 192.168.1.144:7000 55023AE790E26D7FD5527FA8D35C51894CAE741E',
            'test001a orport=5001 no-v2 hs v3ident=9715CA5123D1D5D2AF0387BFA5EFEA30A3A5910C 192.168.1.144:7001 3944B4F38F417A8FCA2EE2C96311D2A65D23B1E3',
            'test002a orport=5002 no-v2 hs v3ident=A897BAA0016FA9564342463A4249681F4D940AEB 192.168.1.144:7002 2D2BDE3BEA76A85FC5B5D310E6FD2225C5FA0F1A'
        ]
        self.config.save()

        d = txtorcon.launch_tor(
            self.config,
            reactor,
            tor_binary='C:\\Program Files (x86)\\Tor\\tor.exe',
            progress_updates=self.progress)
        d.addCallback(self.launched).addErrback(self.error)

    @defer.inlineCallbacks
    def launched(self, process_proto):
        log.msg("Tor has launched.")
        hidden_service_dir = os.path.join(
            self.config.DataDirectory, 'hidden_service')

        # Starts the listening server
        endpoint = txtorcon.TCPHiddenServiceEndpoint(
            reactor, self.config,
            7701, hidden_service_dir=hidden_service_dir)
        self.port = yield endpoint.listen(self.factory)

    def error(self, failure):
        log.msg("There was an error", failure.getErrorMessage())
        reactor.stop()

    def progress(self, percent, tag, summary):
        ticks = int((percent / 100.0) * 10.0)
        prog = (ticks * '#') + ((10 - ticks) * '.')
        log.msg('%s %s' % (prog, summary))
