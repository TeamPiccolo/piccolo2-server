"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloInstrument']

import logging

class PiccoloInstrument(object):
    """base class used to define instruments attached to the piccolo system
    """

    LOGBASE = 'piccolo.instrument'

    def __init__(self,name):
        """
        :param name: name of the component"""
        self._name = name
        self._log = logging.getLogger('{0}.{1}'.format(self.LOGBASE,name))

        self.log.info("initialised")

    @property
    def name(self):
        """the name of the component"""
        return self._name

    @property
    def log(self):
        """get the logger"""
        return self._log

    def ping(self):
        """ping instrument

        :return: *pong*"""
        
        self.log.debug("ping")
        return 'pong'

    def status(self):
        """get instrument status

        :return: *ok*"""
        self.log.debug("status")
        return 'ok'

    def stop(self):
        """stop instrument"""
        self.log.debug("stopped")
        return 'ok'

if __name__ == '__main__':
    from piccoloLogging import *

    piccoloLogging(debug=True)
    p = PiccoloInstrument("test")
    print p.ping()
    print p.status()
