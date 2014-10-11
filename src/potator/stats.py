import threading
import time


class StatPrinter(threading.Thread):

    def __init__(self, tor, tun):
        threading.Thread.__init__(self)
        self.tor = tor
        self.tun = tun
        self.running = True

    def run(self):
        while self.running:
            # print 'TOR: S: %sb R: %sb'
            time.sleep(1)
            print 'TUN: S: %db R: %db\r' % (self.tun.sent_bytes,
                                            self.tun.received_bytes),

    def stop(self):
        self.running = False
