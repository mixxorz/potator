import _winreg as reg
import threading
from struct import unpack

import pywintypes
import win32event
import win32file
from impacket import ImpactDecoder


class TunInterface(object):

    def __init__(self):
        self.tuntap = openTunTap()

        self.transmitter = Transmitter(self.tuntap)
        self.readThread = ReadThread(self.tuntap, self)

    def start(self):
        self.readThread.start()

    def stop(self):
        self.readThread.close()
        win32file.CloseHandle(self.tuntap)

    def write(self, data):
        self.transmitter.transmit(data)

    def packetReceived(self, packet):
        raise NotImplementedError()

#============================ defines =========================================

# IPv4 configuration of your TUN interface (represented as a list of integers)
# < The IPv4 address of the TUN interface.

TUN_IPv4_ADDRESS = [4, 4, 4, 2]

# < The IPv4 address of the TUN interface's network.
TUN_IPv4_NETWORK = [4,  0, 0, 0]
# < The IPv4 netmask of the TUN interface.
TUN_IPv4_NETMASK = [255, 0, 0, 0]

# Key in the Windows registry where to find all network interfaces (don't
# change, this is always the same)
ADAPTER_KEY = r'SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}'

# Value of the ComponentId key in the registry corresponding to your TUN
# interface.
TUNTAP_COMPONENT_ID = 'tap0901'

#======================= external commands ====================================

#============================ helpers =========================================

#=== tun/tap-related functions


def get_tuntap_ComponentId():
    '''
    \brief Retrieve the instance ID of the TUN/TAP interface from the Windows
        registry,

    This function loops through all the sub-entries at the following location
    in the Windows registry: reg.HKEY_LOCAL_MACHINE, ADAPTER_KEY

    It looks for one which has the 'ComponentId' key set to
    TUNTAP_COMPONENT_ID, and returns the value of the 'NetCfgInstanceId' key.

    \return The 'ComponentId' associated with the TUN/TAP interface, a string
        of the form "{A9A413D7-4D1C-47BA-A3A9-92F091828881}".
    '''
    with reg.OpenKey(reg.HKEY_LOCAL_MACHINE, ADAPTER_KEY) as adapters:
        try:
            for i in xrange(10000):
                key_name = reg.EnumKey(adapters, i)
                with reg.OpenKey(adapters, key_name) as adapter:
                    try:
                        component_id = reg.QueryValueEx(
                            adapter, 'ComponentId')[0]
                        if component_id == TUNTAP_COMPONENT_ID:
                            return reg.QueryValueEx(
                                adapter, 'NetCfgInstanceId'
                            )[0]
                    except WindowsError:
                        pass
        except WindowsError:
            pass


def CTL_CODE(device_type, function, method, access):
    return (device_type << 16) | (access << 14) | (function << 2) | method


def TAP_CONTROL_CODE(request, method):
    return CTL_CODE(34, request, method, 0)

TAP_IOCTL_SET_MEDIA_STATUS = TAP_CONTROL_CODE(6, 0)
TAP_IOCTL_CONFIG_TUN = TAP_CONTROL_CODE(10, 0)


def openTunTap():
    '''
    \brief Open a TUN/TAP interface and switch it to TUN mode.

    \return The handler of the interface, which can be used for later
        read/write operations.
    '''

    # retrieve the ComponentId from the TUN/TAP interface
    componentId = get_tuntap_ComponentId()
    print('componentId = {0}'.format(componentId))

    # create a win32file for manipulating the TUN/TAP interface
    tuntap = win32file.CreateFile(
        r'\\.\Global\%s.tap' % componentId,
        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_ATTRIBUTE_SYSTEM | win32file.FILE_FLAG_OVERLAPPED,
        None
    )
    print('tuntap      = {0}'.format(tuntap.handle))

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

    # return the handler of the TUN interface
    return tuntap


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

    def __init__(self, tuntap, interface):

        # store params
        self.tuntap = tuntap
        self.interface = interface

        # local variables
        self.goOn = True
        self.overlappedRx = pywintypes.OVERLAPPED()
        self.overlappedRx.hEvent = win32event.CreateEvent(None, 0, 0, None)

        # initialize parent
        threading.Thread.__init__(self)

        # give this thread a name
        self.name = 'readThread'

    def run(self):

        rxbuffer = win32file.AllocateReadBuffer(self.ETHERNET_MTU)

        print TUN_IPv4_ADDRESS

        while self.goOn:

            # wait for data
            l, p = win32file.ReadFile(self.tuntap, rxbuffer, self.overlappedRx)

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

                self.interface.packetReceived(ip_packet)

    def close(self):
        self.goOn = False


class Transmitter(object):

    def __init__(self, tuntap):

        self.tuntap = tuntap
        self.goOn = True
        self.overlappedTx = pywintypes.OVERLAPPED()
        self.overlappedTx.hEvent = win32event.CreateEvent(None, 0, 0, None)

    def transmit(self, dataToTransmit):

        # write over tuntap interface
        win32file.WriteFile(self.tuntap, dataToTransmit, self.overlappedTx)
        win32event.WaitForSingleObject(
            self.overlappedTx.hEvent, win32event.INFINITE)
        self.overlappedTx.Offset = self.overlappedTx.Offset + \
            len(dataToTransmit)
