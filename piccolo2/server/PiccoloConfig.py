"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloConfig']

import os.path
import logging
from configobj import ConfigObj, flatten_errors
from validate import Validator

# the defaults
defaultCfgStr = """
# There are two channels for light: Upwelling and Downwelling. This section
# associates a shutter (1, 2 or 3) and a fibre with each channel. This
# information is required to ensure that the correct shutter (1, 2 or 3) is
# openend to record each spectrum. This section also includes information about
# the optical fibre used for each channel. This information is not used by the
# Piccolo, but it is saved in the meatadata (header) section of data (Pico)
# files.
#
# If the polarity of a shutter connection has been reversed the shutter will
# be open when it should be closed; and closed when it should be open. If this
# happens, try changing Reverse from false to true.

[channels]
  [[__many__]]
    shutter = integer(default=-1)
    reverse = boolean(default=False) # Is the polarity of the shutter connection reversed?
    fibreDiameter = integer(default=600) # micrometres

# Some spectrometers have adjustable configuration options. For example, the
# Ocean Optics NIRQuest 512 spectrometer has a detector which is cooled (or
# heated) by a thermoelectric cooler. The temperature to which the detector will
# be cooled can be adjusted. A cooler temperature will reduce the electronic
# noise in the signal and increase the power consumption. The spectrometer's fan
# can also be turned on or off. These settings will be applied when the
# Piccolo's hardware is initialized. The settings will be applied only to the
# spectrometer with the given serial number.
[spectrometers]
  [[__many__]]
    detectorTemperature = float(default=None)
    fan = boolean(default=None)
"""

# populate the default  config object which is used as a validator
piccoloDefaults = ConfigObj(defaultCfgStr.split('\n'))
validator = Validator()

class PiccoloConfig(object):
    """object managing the piccolo configuration"""

    def __init__(self):
        self._log = logging.getLogger('piccolo.config')
        self._cfg = ConfigObj(configspec=piccoloDefaults)
        self._cfg.validate(validator)

    def readCfg(self,fname):
        """read and parse configuration file"""

        if not os.path.isfile(fname):
            msg = 'no such configuration file {0}'.format(fname)
            self.log.error(msg)
            raise RuntimeError, msg


        self._cfg.filename = fname
        self._cfg.reload()
        if not self._cfg.validate(validator):
            msg = 'Could not read config file {0}'.format(fname)
            self.log.error(msg)
            raise RuntimeError, msg

    @property
    def log(self):
        return self._log

    @property
    def cfg(self):
        return self._cfg

if __name__ == '__main__':
    import sys

    cfg = PiccoloConfig()

    if len(sys.argv)>1:
        cfg.readCfg(sys.argv[1])

    print cfg.cfg
