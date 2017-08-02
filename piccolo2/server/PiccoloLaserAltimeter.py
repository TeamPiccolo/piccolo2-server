from PiccoloInstrument import PiccoloAuxInstrument
import threading
import time
import threading
from Queue import Queue
import logging
import serial


class Altimeter(threading.Thread):
    """Simple software interface to a peripheral altimeter device,
    can request and retrieve altitude
    """
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        while True:
            time.sleep(1)

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
    Polling mode: altimeter sends readings constantly
    On demand mode: send 'd' to altimeter to retrieve reading
    """
    def __init__(self,port=None,baudrate=None,timeout=2,mode='polling'):
        self._ser = serial.Serial(port,baudrate,timeout=timeout)
        self._latestAltitude = 'N/A'
        self.mode = mode
        Altimeter.__init__(self)
   

    def _readAltitudeFromSerial(self):
            record = self._ser.readline()
            try:
                self._latestAltitude = record.strip().split()[0]
            except Exception:
                self._latestAltitude = 'N/A'

    def run(self):
        while(True):
            if self.mode == 'ondemand':
                #in on demand mode, buffer only gets written to when requested
                continue
            else:
                #in polling mode, buffer must be constantly flushed
                self._readAltitudeFromSerial()

        
    def requestInstrumentMeasurement(self):
        if self.mode == 'ondemand':
            self._ser.write(b'd')
            self._readAltitudeFromSerial()

    def retrieveInsturmentResponse(self):
        return self._latestAltitude

class DummyAltimeter(Altimeter):
    """Dummy implementation of Altimeter that waits .1s to return a reading
    """
    def requestInstrumentMeasurement(self):
        pass

    def retrieveInsturmentResponse(self):
        time.sleep(.1)
        return -1
 
class PiccoloAltimeter(PiccoloAuxInstrument):
    def __init__(self, name, altimeter=None):
        PiccoloAuxInstrument.__init__(self, name)
        self._altimeter = altimeter
        self._altimeter.start()

    def getRecord(self):
        return self._altimeter.getAltitude()


if __name__ == '__main__':    
    pa = PiccoloAltimeter("alt",LightWareSF11Altimeter('/dev/ttyUSB0',115200))
    while True:
        print(pa.getRecord())
        time.sleep(.1)
