from PiccoloInstrument import PiccoloAuxInstrument
from PiccoloWorkerThread import PiccoloWorkerThread
import time
import threading
from Queue import Queue
import logging
import serial


class Altimeter(object):
    """Simple software interface to a peripheral altimeter device,
    can request and retrieve altitude
    """
    def requestInstrumentMeasurement(self):
        raise NotImplemented

    def retrieveInsturmentResponse(self):
        raise NotImplemented

    def getAltitude(self):
        self.requestInstrumentMeasurement()
        return self.retrieveInsturmentResponse()


class LightWareSF11Altimeter(Altimeter):
    """Interface for Lightware SF11 Laser Altimeter
    https://www.mikrocontroller.com/images/SF11ManualRev4.pdf
    """
    def __init__(self,device,baudrate,timeout=2):
        self._ser = serial.Serial(device,baudrate,timeout=timeout)

    def requestInstrumentMeasurement(self):
        self._ser.write('d')

    def retrieveInsturmentResponse(self):
        return self._ser.readline() 

class DummyAltimeter(Altimeter):
    """Dummy implementation of Altimeter that waits .1s to return a reading
    """
    def requestInstrumentMeasurement(self):
        pass

    def retrieveInsturmentResponse(self):
        time.sleep(.1)
        return -1
 
class AltimeterThread(PiccoloWorkerThread):
    """Altimeter worker thread object
    Subclassing PiccoloWorkerThread may be overkill
    """
    def __init__(self, name, altimeter, busy, tasks, results):
        PiccoloWorkerThread.__init__(self, name, busy, tasks, results)
        self._alt = altimeter

    def run(self):
        while True:
            # wait for a new task from the task queue
            task = self.tasks.get()
            if task == None:
                # The worker thread can be stopped by putting a None onto the task queue.
                self.log.info('Stopped worker thread for altimeter {}.'.format(self.name))
                return
            if task[0] == "get":
                try:
                    self.results.put(("ok",self._alt.getAltitude()))
                except Exception as e:
                    self.results.put(("nok",str(e)))



class PiccoloAltimeter(PiccoloAuxInstrument):
    def __init__(self, name, altimeter=DummyAltimeter()):
        PiccoloAuxInstrument.__init__(self, name)

        # The lock prevents two threads using the spectrometer at the same time.
        self._busy = threading.Lock()
        self._tQ = Queue() # Task queue.
        self._rQ = Queue() # Results queue.

        self._altimeter = AltimeterThread(name, altimeter, self._busy, self._tQ, self._rQ)
        self._altimeter.start()


    def getRecord(self):
        self._tQ.put(("get",))
        status,result = self._rQ.get()
        if status == "ok":
            return result
        elif status == "nok":
            self.log.error("Altitude measurement error: {}".format(result))
            return "N/A"


if __name__ == '__main__':    
    pa = PiccoloAltimeter("alt",DummyAltimeter())
    while True:
        print(pa.getRecord())
        time.sleep(4)
