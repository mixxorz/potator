import threading
import time


class StatPrinter(threading.Thread):

    def __init__(self, tor, tun):
        threading.Thread.__init__(self)
        self.tor = tor
        self.tun = tun
        self.running = True

    def run(self):
        prev_sent = 0
        prev_recv = 0
        while self.running:
            # print 'TOR: S: %sb R: %sb'
            cur_sent = self.tun.sent_bytes
            cur_recv = self.tun.received_bytes

            speed_sent = (cur_sent - prev_sent)
            speed_recv = (cur_recv - prev_recv)

            print '\r                                                         ',
            print '\rCurrent speed: S: %dkb/s R: %dkb/s' % (speed_sent / 1024,
                                                            speed_recv / 1024),

            prev_sent = cur_sent
            prev_recv = cur_recv

            # print 'TUN: S: %db R: %db\r' % (self.tun.sent_bytes,
            #                                 self.tun.received_bytes),
            time.sleep(1)

    def stop(self):
        self.running = False
