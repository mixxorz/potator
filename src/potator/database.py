""" Handles temporary storage of Onion URL - IP address mappings
"""

from twisted.python import log


class OnionIPMapper(object):
    """ Holds mappings and provides an API to get and set mappings

    :cvar mappings: A Python dictionary with the key as the IP address, and \
                    the value as the onion URL
    """

    def __init__(self):
        self.mappings = {}

    def getOnionUrl(self, ip_address):
        """ Get the onion URL that corresponds to the :code:`ip_address`

        :param str ip_address: The IP address
        :return: The onion URL
        :rtype: str
        """
        value = self.mappings.get(ip_address)
        if not value:
            log.msg('Unknown IP address: %s' % ip_address)
        return value

    def setOnionUrl(self, ip_address, onion_url):
        """ Sets a mapping between an IP address and an onion URL

        :param str ip_address: The IP address
        :param str onion_url: The onion URL
        """
        self.mappings[ip_address] = onion_url
        log.msg('Saving: %s = %s' % (ip_address, onion_url))

    def getAllOnionUrls(self):
        """ Get all onion URLs in :code:`mappings`

        :return: A list of onion URLs
        :rtype: list
        """
        return [value for key, value in self.mappings.iteritems()]

    def getAllMappings(self):
        """ Get the mappings class variable

        :return: The mappings class variable
        :rtype: dict
        """
        return self.mappings
