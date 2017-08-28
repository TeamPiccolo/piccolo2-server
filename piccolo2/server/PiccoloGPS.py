from PiccoloInstrument import PiccoloAuxInstrument, PiccoloAuxHandlerThread


class AdafruitGPS(PiccoloAuxHandlerThread):
    def __init__(self,host='localhost',port='2947'):
        #adafruit GPS module, sudo apt-get install python-gps
        import gps
        self.gpsd = gps.gps(host,port)
        self.gpsd.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
        
        self.current_value = {}
        self.running = True #setting the thread running to true

        PiccoloAuxHandlerThread.__init__(self)
 
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

    def getRecord(self,keys=('lat', 'lon', 'time', 'speed', 'alt',)):
        return {k:self.current_value.get(k,'N/A') for k in keys}

if __name__ == '__main__':
    import time
    pgps = PiccoloAuxInstrument('GPS',AdafruitGPS())
    try:
        while 1:
            time.sleep(1)
            print(pgps.getRecord())
    except KeyboardInterrupt:
        pgps.stop()
        exit(0)
