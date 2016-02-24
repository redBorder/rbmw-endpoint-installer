import yaml
import logging

# Create an object for configuration
class Config():

    # Properties in dictionary format
    properties = None

    # Default config file path
    CONFIG_FILE = "config.yml"

    # Main constructor
    def __init__(self, path):
        self.CONFIG_FILE = path
        self.reload()

    # Reload config file
    def reload(self):
        configFile = open(self.CONFIG_FILE, 'r')
        self.properties = yaml.load(configFile.read())
        configFile.close()
        logging.getLogger('application').info("Config loaded from : {0}".format(self.CONFIG_FILE))


    # Get string value from key
    def get(self, key, defaultValue):
        return self.properties[key] if self.properties.has_key(key) else defaultValue


    # Get list value from key
    def getList(self, key, defaultValue):
        if not  self.properties.has_key(key):
            return defaultValue
        else:
            return str(self.properties[key]).split()


    # Get boolean value from key
    def getBoolean(self, key, defaultValue):
        return bool(self.properties[key]) if self.properties.has_key(key) else defaultValue


    # Get integer value from key
    def getInt(self, key, defaultValue):
        return int(self.properties[key]) if self.properties.has_key(key) else defaultValue


    # Get configuration properties
    def getConfigProperties(self):
        return self.properties



