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
