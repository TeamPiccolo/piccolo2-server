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

__all__ = ['PiccoloShutter']

from PiccoloInstrument import PiccoloInstrument
import threading
import time

def shutter(shutter,milliseconds):
    """worker function used to open the shutter for the set period

    :param shutter: the shutter instance to operate on
    :type shutter: PiccoloShutter
    :param milliseconds: time to leave shutter open in milliseconds"""
    assert isinstance(shutter,PiccoloShutter)
    
    result = shutter.openShutter()
    if result!='ok':
        return result
    time.sleep(milliseconds/1000.)
    result = shutter.closeShutter()
    return result
    

class PiccoloShutter(PiccoloInstrument):
    """class used to control a shutter"""

    def __init__(self,name,shutter=None,reverse=False,fibreDiameter=600.):
        """
        :param name: name of the component
        :param shutter: the shutter object, if None use dummy
        :param reverse: reverse the polarity of the shutter
        :param fibreDiameter: the diameter of the fibre, used for info
        """

        PiccoloInstrument.__init__(self,name)
        self._lock = threading.Lock()
        
        self._fibre = float(fibreDiameter)
        self._reverse = reverse

        self._shutter = shutter
        if self._shutter!=None:
            self.openShutter()
            time.sleep(1)
            self.closeShutter()

    @property
    def reverse(self):
        """whether polarity is reversed"""
        return self._reverse

    @property
    def fibreDiameter(self):
        """the diameter of the optical fibre"""
        return self._fibre
    
    def openShutter(self):
        """open the shutter"""

        if self._lock.locked():
            self.log.warn('shutter already open')
            return 'shutter already open'
        self._lock.acquire()
        self.log.info('open shutter')
        if self._shutter!=None:
            self._shutter.open()
        return 'ok'
        
    def closeShutter(self):
        """close the shutter"""
        
        if not self._lock.locked():
            self.log.warn('shutter already closed')
            return 'shutter already closed'
        if self._shutter!=None:
            self._shutter.close()
        self._lock.release()
        self.log.info('closed shutter')
        return 'ok'

    def open_close(self,milliseconds=1000):
        """open the shutter for a set period

        :param milliseconds: time to leave shutter open in milliseconds"""

        self.log.info('opening the shutter for {0} milliseconds'.format(milliseconds))

        t = threading.Thread(target = shutter, args = (self,milliseconds),name=self.name)
        t.daemon=True
        t.start()
                             
    def status(self):
        """return status of shutter

        :return: *open* if the shutter is open or *closed* if it is closed"""

        if self._lock.locked():
            return 'open'
        else:
            return 'closed'


    def info(self):
        """get info

        :returns: dictionary containing shutter information
        :rtype: dict"""

        return {'fibreDiameter': self.fibreDiameter,
                'reverse':       self.reverse,
                'status':        self.status()}

if __name__ == '__main__':
    from piccoloLogging import *

    piccoloLogging(debug=True)

    s = PiccoloShutter('shutter')

    s.openShutter()
    s.openShutter()
    s.closeShutter()
    s.closeShutter()

    s.open_close(5000)
    s.openShutter()

    time.sleep(6)

    s.open_close(5000)
    time.sleep(2)
    s.closeShutter()
    time.sleep(4)
