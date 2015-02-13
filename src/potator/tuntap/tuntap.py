import _winreg as reg
import threading
from Queue import Queue
from struct import unpack

import ipaddr
import pythoncom
import pywintypes
import win32event
import win32file
import wmi
from impacket import ImpactDecoder
from twisted.internet import defer, task, threads, reactor


class TunInterface(object):

    def __init__(self, potator):
        self.potator = potator

        self.sent_bytes = 0
        self.received_bytes = 0

        self.readThread = ReadThread(self)
        self.writeThread = WriteThread(self)
        self.started = False
        self.failed = False

        self.writeBuffer = Queue()

        self._runner_loop = task.LoopingCall(self._runner)
        self._runner_loop.start(5.0)

    def stop(self):
        try:
            self.readThread.close()
            self.writeThread.close()
            win32file.CloseHandle(self.tuntap)
        except Exception:
            pass

    @defer.inlineCallbacks
    def _runner(self):
        if not self.readThread.goOn or not self.writeThread.goOn:
            self.failed = True

        if self.failed or not self.started:
            self.started = True
            self.failed = False
            self.stop()

            try:
                self.tuntap = yield threads.deferToThread(self._openTunTap)
            except Exception, e:
                print 'ERROR:', e
                reactor.stop()
            self.readThread = ReadThread(self)
            self.writeThread = WriteThread(self)
            self.readThread.daemon = True
            self.writeThread.daemon = True
            self.readThread.start()
            self.writeThread.start()

    def _openTunTap(self):
        pythoncom.CoInitialize()

        interface = get_available_tuntap_interface()

        tuntap = win32file.CreateFile(
            r'\\.\Global\%s.tap' % interface.SettingID,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_SYSTEM | win32file.FILE_FLAG_OVERLAPPED,
            None
        )

        # Rename interface
        connection_key = INSTANCE_KEY + '\\' + \
            interface.SettingID + '\\Connection'
        with reg.OpenKey(reg.HKEY_LOCAL_MACHINE, connection_key, 0,
                         reg.KEY_ALL_ACCESS) as instance:
            reg.SetValueEx(
                instance, 'Name', 0, reg.REG_SZ,
                self.potator.config['NETWORK_ID'])
            print 'Using interface', reg.QueryValueEx(instance, 'Name')[0]

        # have Windows consider the interface now connected
        win32file.DeviceIoControl(
            tuntap,
            TAP_IOCTL_SET_MEDIA_STATUS,
            '\x01\x00\x00\x00',
            None
        )

        # prepare the parameter passed to the TAP_IOCTL_CONFIG_TUN commmand.
        # This needs to be a 12-character long string representing
        # - the tun interface's IPv4 address (4 characters)
        # - the tun interface's IPv4 network address (4 characters)
        # - the tun interface's IPv4 network mask (4 characters)

        ip_address = ipaddr.IPv4Network(self.potator.config['IP_NETWORK'])
        TUN_IPv4_ADDRESS = [int(x) for x in str(ip_address.ip).split('.')]
        TUN_IPv4_NETWORK = [int(x) for x in str(ip_address.network).split('.')]
        TUN_IPv4_NETMASK = [int(x) for x in str(ip_address.netmask).split('.')]

        configTunParam = []
        configTunParam += TUN_IPv4_ADDRESS
        configTunParam += TUN_IPv4_NETWORK
        configTunParam += TUN_IPv4_NETMASK
        configTunParam = ''.join([chr(b) for b in configTunParam])

        # switch to TUN mode (by default the interface runs in TAP mode)
        win32file.DeviceIoControl(
            tuntap,
            TAP_IOCTL_CONFIG_TUN,
            configTunParam,
            None
        )

        # Set the IP address and Subnet mask statically
        interface.EnableStatic(
            IPAddress=[unicode(ip_address.ip)],
            SubnetMask=[unicode(ip_address.netmask)])

        # return the handler of the TUN interface
        return tuntap


ADAPTER_KEY = r'SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}'
INSTANCE_KEY = r'SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}'


TUNTAP_COMPONENT_ID = 'tap0901'


def CTL_CODE(device_type, function, method, access):
    return (device_type << 16) | (access << 14) | (function << 2) | method


def TAP_CONTROL_CODE(request, method):
    return CTL_CODE(34, request, method, 0)

TAP_IOCTL_SET_MEDIA_STATUS = TAP_CONTROL_CODE(6, 0)
TAP_IOCTL_CONFIG_TUN = TAP_CONTROL_CODE(10, 0)


def get_available_tuntap_interface():
    nic_configs = wmi.WMI().Win32_NetworkAdapterConfiguration()
    for interface in nic_configs:
        if interface.ServiceName == 'tap0901':
            if not interface.IPEnabled:
                return interface

    raise Exception("No available TAP-Windows adapter")


#============================ threads =========================================
class ReadThread(threading.Thread):

    # TODO: Change text
    '''
    \brief Thread which continously reads input from a TUN interface.

    If that input is an IPv4 echo request (a "ping" command) issued to
    any IP address in the virtual network behind the TUN interface, this thread
    answers with the appropriate echo reply.
    '''

    ETHERNET_MTU = 1500
    IPv6_HEADER_LENGTH = 40

    def __init__(self, interface):

        # store params
        self.interface = interface

        # local variables
        self.goOn = False
        self.overlappedRx = pywintypes.OVERLAPPED()
        self.overlappedRx.hEvent = win32event.CreateEvent(None, 0, 0, None)

        # initialize parent
        threading.Thread.__init__(self)

        # give this thread a name
        self.name = 'readThread'

    def run(self):
        self.goOn = True

        rxbuffer = win32file.AllocateReadBuffer(self.ETHERNET_MTU)

        while self.goOn:

            # wait for data
            try:
                l, p = win32file.ReadFile(
                    self.interface.tuntap, rxbuffer, self.overlappedRx)
            except Exception:
                print 'Tun adapter failed. Recovering...'
                self.goOn = False
                break

            win32event.WaitForSingleObject(
                self.overlappedRx.hEvent, win32event.INFINITE)

            self.overlappedRx.Offset = self.overlappedRx.Offset + len(p)

            ip_header = p[0:20]
            iph = unpack('!BBHHHBBH4s4s', ip_header)
            version_ihl = iph[0]
            version = version_ihl >> 4  # ip version
            ihl = version_ihl & 0xf

            # check if the IP Header exists
            if ihl and version == 4:

                decoder = ImpactDecoder.IPDecoder()
                ip_packet = decoder.decode(p)

                self.interface.potator.outgoingCallback(ip_packet)

    def close(self):
        self.goOn = False


class WriteThread(threading.Thread):

    '''
    \brief Thread with periodically sends IPv4 and IPv6 echo requests.
    '''

    def __init__(self, interface):

        # store params
        self.interface = interface

        # local variables
        self.goOn = False
        self.overlappedTx = pywintypes.OVERLAPPED()
        self.overlappedTx.hEvent = win32event.CreateEvent(None, 0, 0, None)

        # initialize parent
        threading.Thread.__init__(self)

        # give this thread a name
        self.name = 'writeThread'

    def run(self):
        self.goOn = True

        while self.goOn:
            # Receive packet from packet handler
            p = self.interface.writeBuffer.get()
            self.interface.received_bytes += p.get_size()
            # Write to tuntap (transmit)
            self.transmit(p.get_packet())

    def close(self):
        self.goOn = False

    def transmit(self, dataToTransmit):

        # write over tuntap interface
        win32file.WriteFile(
            self.interface.tuntap, dataToTransmit, self.overlappedTx)
        win32event.WaitForSingleObject(
            self.overlappedTx.hEvent, win32event.INFINITE)
        self.overlappedTx.Offset = self.overlappedTx.Offset + \
            len(dataToTransmit)
