from twisted.python import log


class OnionIPMapper(object):

    def __init__(self):
        self.mappings = {}

    def getOnionUrl(self, ip_address):
        value = self.mappings.get(ip_address)
        if not value:
            log.msg('Unknown IP address: %s' % ip_address)
        return value

    def setOnionUrl(self, ip_address, onion_url):
        self.mappings[ip_address] = onion_url
        log.msg('Saving: %s = %s' % (ip_address, onion_url))

    def getAllOnionUrls(self):
        return [value for key, value in self.mappings.iteritems()]

    def getAllMappings(self):
        return [(key, value) for key, value in self.mappings.iteritems()]
