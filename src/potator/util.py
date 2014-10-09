''' Utility classes for Potator
'''
import json
import os


class Settings(object):

    ''' Loads settings from settings.json

    settings.json can be found in %AppData%\\potator\\settings.json
    '''
    _DEFAULTS = {
        'SOCKS_PORT': '7700',
        'HIDDEN_SERVICE_PORT': '7701',
        'SERVER_PORT': '7702',
        'CONTROL_PORT': '7703',
        'ONION_URL': '123.onion'
    }

    _TYPES = {
        'SOCKS_PORT': 'int',
        'HIDDEN_SERVICE_PORT': 'int',
        'SERVER_PORT': 'int',
        'CONTROL_PORT': 'int',
        'ONION_URL': 'unicode'
    }

    def __init__(self):
        self.app_dir = os.path.join(os.environ['AppData'], 'potator')
        self.config = None

        # Create the app folder if it doesn't exist
        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir)
            f = open(os.path.join(self.app_dir, 'settings.json'), 'w')
            f.write(json.dumps(self._DEFAULTS, sort_keys=True, indent=4))
            f.close()

        # Load config from defaults
        self.config = self._DEFAULTS.copy()
        # Load AppData settings.json
        f = open(os.path.join(self.app_dir, 'settings.json'), 'r')
        loaded_config = json.loads(f.read())
        f.close()
        self.config.update(loaded_config)

    def get(self, key):
        ''' Returns the value of a key as its data type

        Arguments:
        key -- the settings key to return
        '''
        if key in self.config:
            type = self._TYPES.get(key, 'unicode')

            if type is 'int':
                return int(self.config.get(key, None))
            elif type is 'unicode':
                return unicode(self.config.get(key, None))
        else:
            return None

    def __getattr__(self, key):
        if key in self.config:
            return self.get(key)
        else:
            raise AttributeError


settings = Settings()
