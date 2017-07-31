from PiccoloInstrument import PiccoloAuxInstrument
import threading

try:
    import gps
    HAS_GPS = True
except:
    HAS_GPS = False

class GpsPoller(threading.Thread):
    def __init__(self,host,port):
        threading.Thread.__init__(self)
        self.daemon=True
        self.gpsd = gps.gps(host,port)
        self.gpsd.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
        
        self.current_value = None
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
                #print "gps time:", report['time']
            #else:
            #   if self.running:
            #      time.sleep(0.01)

	print "GpsPoller finished"



class PiccoloGPS(PiccoloAuxInstrument):
    def __init__(self,name,host="localhost",port="2947"):
        PiccoloAuxInstrument.__init__(self,name)
        self.connected = HAS_GPS
        if HAS_GPS:
            self._gpsp = GpsPoller(host,port)
            self._gpsp.start()

    def getRecord(self,keys=('lat', 'lon', 'time', 'speed', 'alt',)):
        record = (HAS_GPS and self._gpsp.current_value) or {}
        return  {k:record.get(k,'N/A') for k in keys}

    def stop(self):
        self._gpsp.running = False
        self._gpsp.join()

    def __del__(self):
        pass
        #self.stop()

if __name__ == '__main__':
    import time
    pgps = PiccoloGPS('GPS')
    try:
        while 1:
            time.sleep(1)
            print(pgps.getRecord())
    except KeyboardInterrupt:
        pgps.stop()
        exit(0)
