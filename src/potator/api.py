from twisted.python import log
from txjsonrpc.web import jsonrpc


class PotatorAPI(jsonrpc.JSONRPC):

    def __init__(self, potator):
        self.potator = potator

    def jsonrpc_greeting(self, onion_url):
        self.potator.ourp.sendGreeting(onion_url)
        return True

    def jsonrpc_ping(self, onion_url):
        log.msg('Pinging %s' % onion_url)
        self.potator.ping.ping(onion_url)
        return True

    def jsonrpc_get_mappings(self):
        return self.potator.db.getAllMappings()

    def jsonrpc_get_config(self):
        return self.potator.config
