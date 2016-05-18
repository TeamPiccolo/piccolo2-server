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

__all__ = ['PiccoloControllerXbee']

from PiccoloController import PiccoloController
from PiccoloWorkerThread import PiccoloWorkerThread
from piccolo2.hardware import radio
import json
import Queue
import threading
import zlib
import time

class PiccoloXbeeThread(PiccoloWorkerThread):
    LOGNAME = 'xbee'
    CHUNK = 100

    def __init__(self,busy,tasks,results,panid='2525'):

        PiccoloWorkerThread.__init__(self,'xbee',busy,tasks,results)
        self._rd = radio.APIModeRadio(panId=panid)
        self.log.info('xbee serial number %s'%self._rd.getSerialNumber())
        
    def run(self):
        while True:
            try:
                data = self._rd.readBlock(timeoutInSeconds=10)
            except radio.TimeoutError:
                # ignore timeouts, just try again
                # this helps if a client disappears during transmission
                continue

            self.log.debug('got command %s'%data)
            snr,command,component,keywords = json.loads(data)
            snr = str(snr)

            self.tasks.put((command,component,keywords))

            res = json.dumps(self.results.get())

            self._rd.writeBlock(res,snr)

            self.log.debug('done')
            

class PiccoloControllerXbee(PiccoloController):
    def __init__(self,panid='2525'):
        PiccoloController.__init__(self)
        busy = threading.Lock()

        self._worker = PiccoloXbeeThread(busy,self.taskQ,self.doneQ)
        self._worker.start()
    

if __name__ == '__main__':
    xbee = PiccoloControllerXbee()
    #time.sleep(100)
