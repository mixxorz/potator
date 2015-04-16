""" Potator API Module

This module handles API interactions via JSONRPC
"""

from twisted.python import log
from txjsonrpc.web import jsonrpc


class PotatorAPI(jsonrpc.JSONRPC):
    """ Twisted Module that receives and responds to JSONRPC connections
    """

    def __init__(self, potator):
        self.potator = potator

    def jsonrpc_greeting(self, onion_url):
        """ Sends an OURP greeting to onion_url

        Response: None
        """
        self.potator.ourp.sendGreeting(onion_url)
        return True

    def jsonrpc_ping(self, onion_url):
        """ Sends an OURP ping to onion_url

        Response: None
        """
        log.msg('Pinging %s' % onion_url)
        self.potator.ping.ping(onion_url)
        return True

    def jsonrpc_get_mappings(self):
        """ Responds with the Onion Url - IP Address mappings

        Response: The Onion Url - IP Address mappings of this instance of
                  Potator
        """
        return self.potator.db.getAllMappings()

    def jsonrpc_get_config(self):
        """ Responds with this Potator instance's configuration

        Response: Dictionary containing the Potator configuration
        """
        return self.potator.config
