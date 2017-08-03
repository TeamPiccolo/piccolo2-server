# Copyright 2014-2016 The Piccolo Team
#
# This file is part of piccolo2-server.
#
# piccolo2-server is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# piccolo2-server is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with piccolo2-server.  If not, see <http://www.gnu.org/licenses/>.

"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloInstrument']

import logging
import threading

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



class PiccoloAuxHandlerThread(threading.Thread):
    """Thread to poll/query an attached peripheral instrument
    Interfaces with rest of program through PiccoloAuxInstrument
    """
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self._isConnected = self._testConnection()

    def _testConnection(self):
        """Test whether the hardware is connected"""
        return True

    @property
    def connected(self):
        return self._isConnected

    def run(self):
        raise NotImplementedError

    def requestInstrumentMeasurement(self):
        raise NotImplementedError

    def retrieveInstrumentResponse(self):
        raise NotImplementedError

    def getRecord(self):
        self.requestInstrumentMeasurement()
        return self.retrieveInstrumentResponse()

class PiccoloAuxInstrument(PiccoloInstrument):
    """class used to define non-essential metadata gathering instruments 
    attached to the piccolo system. Relays information between an
    instrument's driver thread and the rest of the system
    """
    def __init__(self,name,handlerThread=None):
        PiccoloInstrument.__init__(self,name)
        self._handlerThread = handlerThread
        if handlerThread:
            handlerThread.start()

    def getRecord(self):
        return self._handlerThread.getRecord()

if __name__ == '__main__':
    from piccoloLogging import *

    piccoloLogging(debug=True)
    p = PiccoloInstrument("test")
    print p.ping()
    print p.status()
