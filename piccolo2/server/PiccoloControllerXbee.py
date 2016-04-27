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

        PiccoloWorkerThread.__init__(self,'xbee',busy,tasks,results,daemon=False)
        self._rd = radio.APIModeRadio(panId=panid)
        
    def run(self):
        while True:
            data = ''
            d = 'nok'
            while d != 'ok':
                d = self._rd.readline()
                time.sleep(0.1)
                if d=='ok':
                    break
                data += d
            snr,command,component,keywords = json.loads(data)
            snr = str(snr)
            self.log.debug('got command %s'%d)

            self.tasks.put((command,component,keywords))

            res = json.dumps(self.results.get())
            l = len(res)
            n = l//self.CHUNK+1
            for i in range(0,n):
                s = i*self.CHUNK
                e = min((i+1)*self.CHUNK,l)
                self.log.debug('write results (%d) %d/%d'%(e-s,i+1,n))
                self._rd.writeline(res[s:e],snr)
                time.sleep(0.1)
            self._rd.writeline('ok',snr)
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
