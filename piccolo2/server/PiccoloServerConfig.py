"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloServerConfig']

from configobj import ConfigObj
from validate import Validator
from argparse import ArgumentParser

# the defaults
defaultCfgStr = """
# Piccolo Server Configuration
#
# This configuration file controls the basic operation of the piccolo server.
#

[logging]
# enable debugging to get extra verbose log
debug = boolean(default=False)
# log to logfile if set otherwise log to stdout
logfile = string(default=None)

[jsonrpc]
# The URL on which the piccolo JSON-RPC server is listening. By default listen
# on http://localhost:8080
url = string(default="http://localhost:8080")
"""

# populate the default server config object which is used as a validator
piccoloServerDefaults = ConfigObj(defaultCfgStr.split('\n'))
validator = Validator()

class PiccoloServerConfig(object):
    """object managing the piccolo server configuration"""

    def __init__(self):
        self._cfg = ConfigObj(configspec=piccoloServerDefaults)
        self._cfg.validate(validator)

        parser = ArgumentParser()
        parser.add_argument('-c','--configuration-file',metavar='CFG',help="read configuration from CFG")
        parser.add_argument('-d', '--debug', action='store_true',help="enable debugging output")
        parser.add_argument('-l', '--log-file',metavar="FILE",help="send piccolo log to FILE, default stdout")
        parser.add_argument('-u','--piccolo-url',metavar='URL',help="set the URL of the piccolo JSON-RPC server, default {}".format(self._cfg['jsonrpc']['url']))
        
        args = parser.parse_args()
        if args.configuration_file!=None:
            self._cfg.filename = args.configuration_file
            self._cfg.reload()
            self._cfg.validate(validator)
        if args.debug != None:
            self._cfg['logging']['debug'] = args.debug
        if args.log_file != None:
            self._cfg['logging']['logfile'] = args.log_file
        if args.piccolo_url != None:
            self._cfg['jsonrpc']['url'] = args.piccolo_url
        
    @property
    def cfg(self):
        return self._cfg

if __name__ == '__main__':

    cfg = PiccoloServerConfig()
    print cfg.cfg
    

