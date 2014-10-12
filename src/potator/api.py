import sys

from twisted.internet import reactor, protocol
from twisted.protocols import basic
from twisted.python import log


class PotatorApiProtocol(basic.LineReceiver):

    def connectionMade(self):
        self.sendLine("Potator v0.1")

    def lineReceived(self, line):
        # Ignore blank lines
        if not line:
            return

        # Parse the command
        commandParts = line.split()
        command = commandParts.pop(0).lower()
        args = commandParts

        # Dispatch the command to the appropriate method.  Note that all you
        # need to do to implement a new command is add another do_* method.
        try:
            method = getattr(self, 'do_' + command)
        except AttributeError, e:
            self.sendLine('Error: no such command: %s' % command)
        else:
            try:
                method(*args)
            except Exception, e:
                self.sendLine('Error: ' + str(e))

    def do_help(self, command=None):
        """help [command]: List commands, or show help on the given command"""
        if command:
            self.sendLine(getattr(self, 'do_' + command).__doc__)
        else:
            commands = [cmd[3:] for cmd in dir(self) if cmd.startswith('do_')]
            self.sendLine("Valid commands: " + " ".join(commands))

    def do_quit(self):
        """quit: Quit this session"""
        self.sendLine('Goodbye.')
        self.transport.loseConnection()

    def connectionLost(self, reason):
        pass


class PotatorApiFactory(protocol.Factory):

    def __init__(self):
        log.msg('Started Potator API')

    def buildProtocol(self, addr):
        return PotatorApiProtocol()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    reactor.listenTCP(9999, PotatorApiFactory())
    reactor.run()
