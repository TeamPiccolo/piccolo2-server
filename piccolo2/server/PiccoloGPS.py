from PiccoloInstrument import PiccoloAuxInstrument
import threading

try:
    import gps
    HAS_GPS = True
except:
    HAS_GPS = False

class GPS(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        while True:
            time.sleep(1)

    def getLocation(self):
        return {}


class AdafruitGPS(GPS):
    def __init__(self,host='localhost',port='2947'):
        threading.Thread.__init__(self)
        self.daemon=True
        self.gpsd = gps.gps(host,port)
        self.gpsd.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
        
        self.current_value = {}
        self.running = True #setting the thread running to true
 
    def run(self):
        report = {}
        while self.running:
            if self.gpsd.waiting():
                try:
                    #this will continue to loop and grab EACH set 
                    #of gpsd info to clear the buffer
                    report = self.gpsd.next() 
                except AttributeError:
                    #happens when trying to read during cleanup
                    pass

            elif report.get('class',None) == 'TPV':
                self.current_value = report

    def getLocation(self,keys=('lat', 'lon', 'time', 'speed', 'alt',)):
        return {k:self.current_value.get(k,'N/A') for k in keys}

class PiccoloGPS(PiccoloAuxInstrument):
    def __init__(self,name,gps=None):
        PiccoloAuxInstrument.__init__(self,name)
        self.connected = HAS_GPS
        if HAS_GPS:
            self._gpsp = gps
            self._gpsp.start()

    def getRecord(self,):
        return self._gpsp.getLocation()
        
    def stop(self):
        self._gpsp.running = False
        self._gpsp.join()

    def __del__(self):
        pass

if __name__ == '__main__':
    import time
    pgps = PiccoloGPS('GPS',AdafruitGPS())
    try:
        while 1:
            time.sleep(1)
            print(pgps.getRecord())
    except KeyboardInterrupt:
        pgps.stop()
        exit(0)
