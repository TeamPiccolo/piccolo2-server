from PiccoloInstrument import PiccoloAuxInstrument,PiccoloAuxHandlerThread
import time
import logging
import serial

class LightWareSF11Altimeter(PiccoloAuxHandlerThread):
    """Interface for Lightware SF11 Laser Altimeter 
    https://www.mikrocontroller.com/images/SF11ManualRev4.pdf
    Polling mode: altimeter sends readings constantly
    On demand mode: send 'd' to altimeter to retrieve reading
    """
    def __init__(self,port=None,baudrate=None,timeout=2,mode='polling'):
        try:
            self._ser = serial.Serial(port,baudrate,timeout=timeout)
        except:
            #if the serial port can't be opened,set status to disconnected
            self._ser = None
        self._latestAltitude = 'N/A'
        self.mode = mode
        PiccoloAuxHandlerThread.__init__(self)
   

    def _readAltitudeFromSerial(self):
            record = self._ser.readline()
            try:
                self._latestAltitude = record.strip().split()[0]
            except Exception:
                self._latestAltitude = 'N/A'

    def run(self):
        while(True):
            if self.mode=='polling' and self.connected:
                #in polling mode, buffer must be constantly flushed
                self._readAltitudeFromSerial()

        
    def _testConnection(self):
        #if the serial port failed to initialize, we're not connected
        if self._ser is None:
            return False

        #make sure the serial port is sending data
        if self.mode == 'ondemand':
            self._ser.write(b'd')
        return self._ser.readline() != b''

    def requestInstrumentMeasurement(self):
        if self.connected and self.mode == 'ondemand':
            self._ser.write(b'd')
            self._readAltitudeFromSerial()

    def retrieveInstrumentResponse(self):
        if self.connected:
            return self._latestAltitude
        else:
            return "No connection to LightWareSF11Altimeter found" 


if __name__ == '__main__':    
    pa = PiccoloAuxInstrument("alt",LightWareSF11Altimeter('/dev/ttyUSB0',115200))
    while True:
        print(pa.getRecord())
        time.sleep(.1)
