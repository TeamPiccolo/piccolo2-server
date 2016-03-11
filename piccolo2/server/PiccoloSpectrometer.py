"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>
.. moduleauthor:: Iain Robinson <iain.robinson@ed.ac.uk>
"""

__all__ = ['PiccoloSpectrum','PiccoloSpectrometer']

from PiccoloInstrument import PiccoloInstrument
from PiccoloWorkerThread import PiccoloWorkerThread
from collections import MutableMapping
from datetime import datetime
import time
import threading
from Queue import Queue
import logging

protectedKeys = ['Direction','Dark','Datetime']

class PiccoloSpectrum(MutableMapping):
    """An object containing an optical spectrum."""
    def __init__(self):
        self._meta = {}
        self._meta['Direction'] = 'Missing metadata'
        self._meta['Dark'] = 'Missing metadata'
        self._pixels = None
        self.setDatetime()

    def __getitem__(self,key):
        return self._meta[key]

    def __setitem__(self,key,value):
        if key in protectedKeys:
            raise KeyError, 'field {0} is a protected key'.format(key)
        self._meta[key] = value
    
    def __delitem__(self,key):
        if key in protectedKeys:
            raise KeyError, 'field {0} is a protected key'.format(key)
        del self._meta[key]
        
    def __iter__(self):
        return iter(self._meta)

    def __len__(self):
        return len(self._meta)

    def setUpwelling(self,value=None):
        if value == None:
            self._meta['Direction'] = 'Upwelling'
        else:
            assert isinstance(value,bool)
            if value:
                self.setUpwelling()
            else:
                self.setDownwelling()

    def setDownwelling(self):
        self._meta['Direction'] = 'Downwelling'

    def setDark(self,value=None):
        if value==None:
            self._meta['Dark'] = True
        else:
            assert isinstance(value,bool)
            self._meta['Dark'] = value

    def setLight(self):
        self._meta['Dark'] = False
        
    def setDatetime(self,dt=None):
        if dt == None:
            ts = datetime.now()
        elif isinstance(dt,datetime):
            ts = dt
        else:
            ts = datetime.strptime(dt,'%Y-%m-%dT%H:%M:%S')

        self._meta['Datetime'] = '{}Z'.format(ts.isoformat())

    @property
    def pixels(self):
        if self._pixels == None:
            raise RuntimeError, 'The pixel values have not been set.'
        if len(self._pixels) == 0:
            raise RuntimeError, 'There are no pixels in the spectrum.'
        return self._pixels
    @pixels.setter
    def pixels(self,values):
        self._pixels = values

    def getNumberOfPixels(self):
        return len(self.pixels)

class SpectrometerThread(PiccoloWorkerThread):
    """Spectrometer Worker Thread object"""

    LOGNAME = 'spectrometer'

    def __init__(self,name,spectrometer,busy,tasks,results):

        PiccoloWorkerThread.__init__(self,name,busy,tasks,results)

        self._spec = spectrometer

    def run(self):
        while True:
            # wait for a new task from the task queue
            task = self.tasks.get()
            if task == None:
                self.log.info('shutting down')
                return
            else:
                (milliseconds,dark,upwelling) = task
            self.log.info("start recording for {} milliseconds".format(milliseconds))
            self.busy.acquire()

            # create new spectrum instance
            spectrum = PiccoloSpectrum()
            spectrum.setDark(dark)
            spectrum.setUpwelling(upwelling)

            # record data
            if self._spec==None:
                time.sleep(milliseconds/1000.)
                pixels = [1]*100
            else:
                self._spec.setIntegrationTime(milliseconds)
                spectrum.update(self._spec.getMetadata())
                self._spec.requestSpectrum()
                pixels = self._spec.readSpectrum()

            spectrum.pixels = pixels

            # write results to the result queue
            self.results.put(spectrum)
            self.busy.release()
            
class PiccoloSpectrometer(PiccoloInstrument):
    def __init__(self,name,spectrometer=None):
        
        PiccoloInstrument.__init__(self,name)

        self._busy = threading.Lock()
        self._tQ = Queue()
        self._rQ = Queue()

        if spectrometer!=None:
            self._serial = spectrometer.serialNumber
        else:
            self._serial = None

        self._spectrometer = SpectrometerThread(name,spectrometer,self._busy,self._tQ,self._rQ)
        self._spectrometer.start()

    def __del__(self):
        # send poison pill to worker
        self._tQ.put(None)

    def status(self):
        """return status of shutter

        :return: *busy* if recording or *idle*"""

        if self._busy.locked():
            return 'busy'
        else:
            return 'idle'

    def numSpectra(self):
        """get the number of spectra ready to be picked up"""

        return self._rQ.qsize()

    def info(self):
        """get info

        :returns: dictionary containing shutter information
        :rtype: dict"""

        return {'serial' : self._serial,
                'nSpectra' : self.numSpectra(),
                'info' : self.info(),
                'status' : self.status}

    def acquire(self,milliseconds=100,dark=False,upwelling=False):
        """start recording a spectrum

        :param milliseconds: the integration time in milliseconds
        :param dark: whether a dark spectrum is recorded
        :type dark: bool
        :param upwelling: with the direction is upwelling
        :type upwelling: bool
        :return: *ok* if command successful or 'nok: message' if somethign went wrong"""

        if self._busy.locked():
            self.log.warning("already recording a spectrum")
            return 'nok: already recording spectrum'
        self._tQ.put((milliseconds,dark,upwelling))
        return 'ok'

    def getSpectrum(self):
        """get the spectrum"""

        block=True
        if self._busy.locked():
            self.log.debug("busy, waiting until spectrum is available")
            timeout = None
        else:
            self.log.debug("idle, waiting at most 5s for spectrum")
            timeout = 5
        return self._rQ.get(block,timeout)

if __name__ == '__main__':

    from piccoloLogging import *

    piccoloLogging(debug=True)

    nSpec = 2
    specs = []
    for i in range(nSpec):
        specs.append(PiccoloSpectrometer('spectrometer{}'.format(i)))
    for s in specs:
        print s.status()
    for i in range(nSpec):
        specs[i].acquire(milliseconds=(nSpec-i)*2000)
    time.sleep(0.5)
    for s in specs:
        print s.status()
        
    for s in specs:
        spec = s.getSpectrum()
        print spec.getNumberOfPixels()

        
