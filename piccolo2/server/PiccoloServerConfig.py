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

# the piccolo configuration file
# look for config in data directory if the path is relative
config = string(default=piccolo.config)

[logging]
# enable debugging to get extra verbose log
debug = boolean(default=False)
# log to logfile if set otherwise log to stdout
logfile = string(default=None)

[daemon]
# run piccolo server as daemon
daemon = boolean(default=False)
# name of PID file
pid_file = string(default=/var/run/piccolo.pid)

[datadir]
# control location of output files
# if datadir is a relative path (ie it does not start with a /) write to PWD or
# if requested to the mounted device
datadir = string(default=pdata)
# set to true to mount a block device (eg a USB stick) for writing data
mount = boolean(default=False)
# device to be mounted
# Iain Robinson temporarily changed the default device from sda1 to sdb1 for testing.
device = string(default=/dev/sdb1)
# the mount point
mntpnt = string(default=/mnt)

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
        parser.add_argument('-s','--server-configuration',metavar='CFG',help="read configuration from CFG")
        parser.add_argument('-d', '--debug', action='store_true',default=None,help="enable debugging output")
        parser.add_argument('-l', '--log-file',metavar="FILE",help="send piccolo log to FILE, default stdout")

        parser.add_argument('-u','--piccolo-url',metavar='URL',help="set the URL of the piccolo JSON-RPC server, default {}".format(self._cfg['jsonrpc']['url']))

        daemongroup = parser.add_argument_group('daemon')
        daemongroup.add_argument('-D','--daemonize',default=None,action='store_true',help="start piccolo server as daemon")
        daemongroup.add_argument('-p','--pid-file',default=None,help="name of the PID file")
        
        datagroup = parser.add_argument_group('datadir')
        datagroup.add_argument('-o','--data-dir',help="name of data directory, default {}".format(self._cfg['datadir']['datadir']))
        datagroup.add_argument('-m','--mount',default=None,action='store_true',help="mount a device for writing data")

        args = parser.parse_args()

        if args.server_configuration!=None:
            self._cfg.filename = args.server_configuration
            self._cfg.reload()
            self._cfg.validate(validator)
        if args.debug != None:
            self._cfg['logging']['debug'] = args.debug
        if args.log_file != None:
            self._cfg['logging']['logfile'] = args.log_file

        if args.daemonize != None:
            self._cfg['daemon']['daemon'] = args.daemonize
        if args.pid_file != None:
            self._cfg['daemon']['pid_file'] = args.pid_file
            
        if args.piccolo_url != None:
            self._cfg['jsonrpc']['url'] = args.piccolo_url
        if args.data_dir != None:
            self._cfg['datadir']['datadir'] = args.data_dir
        if args.mount != None:
            self._cfg['datadir']['mount'] = args.mount

    @property
    def cfg(self):
        return self._cfg

if __name__ == '__main__':

    cfg = PiccoloServerConfig()
    print(cfg.cfg)
