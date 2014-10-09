import sys
from collections import deque

from twisted.internet import reactor, threads
from threading import Lock

from tor.server import Server
from tuntap.tuntap import TunInterface


class LocalInterface(TunInterface):

    def __init__(self):
        self.lock = Lock()
        self.receive_buffer = deque()
        self.send_buffer = deque()
        TunInterface.__init__(self)

    def packetReceived(self, data):
        self.lock.acquire()
        self.receive_buffer.append(data)
        self.lock.release()

    def write(self, data):
        self.lock.acquire()
        self.send_buffer.append(data)
        self.lock.release()


def sending_loop(server, interface):
    while True:
        if interface.receive_buffer:
            data = interface.receive_buffer.popleft()
            print 'INT: Received Data'


def receiving_loop(server, interface):
    while True:
        if server.receive_buffer:
            data = server.receive_buffer.popleft()
            print 'TOR: Received Data'


def main():
    server = Server(reactor)
    interface = LocalInterface()
    interface.start()

    # To Tor thread
    threads.deferToThread(sending_loop, server, interface)

    # To Local thread
    threads.deferToThread(receiving_loop, server, interface)

    try:
        reactor.run()
    except KeyboardInterrupt:
        print 'Stopping...'
        reactor.stop()
        return 0


if __name__ == '__main__':
    sys.exit(main())
