"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['Piccolo']

from PiccoloInstrument import PiccoloInstrument
from PiccoloDataDir import PiccoloDataDir
from PiccoloWorkerThread import PiccoloWorkerThread
import socket
import psutil
import subprocess
import datetime
import threading
from Queue import Queue
import time

class PiccoloThread(PiccoloWorkerThread):
    """worker thread handling a number of shutters and spectrometers"""

    LOGNAME = 'piccolo'

    def __init__(self,name,shutters,spectrometers,busy,tasks,results):

        PiccoloWorkerThread.__init__(self,name,busy,tasks,results)
        
        self._shutters = shutters
        self._spectrometers = spectrometers

    def _wait(self):
        time.sleep(0.2)

    def _abort(self):
        a = 'no'
        try:
            a = self.task.get(block=False)
        except:
            pass
        if a=='no':
            return False
        elif a=='abort':
            self.log.info('aborted acquisition')
            return True
        else:
            self.log.error('Unexpected command {}'.format(a))
            raise RuntimeError, 'Unexpected command {}'.format(a)
        

    def run(self):
        spectra = []
        while True:
            # wait for a new task from the task queue
            task = self.tasks.get()
            self.log.debug(task)

            if task == None:
                self.log.info('shutting down')
                return
            elif task == 'abort':
                if self.busy.locked():
                    self.results.put(spectra)
                    self.busy.release()
                else:
                    self.log.warn('abort called but not busy')
                    continue
            else:
                (integrationTime,nCycles,delay) = task
                
            # start recording
            self.log.info("start recording {}".format(nCycles))
            self.busy.acquire()

            n = 0
            while True:
                spectra = []
                n = n+1
                if nCycles!='Inf' and n > nCycles:
                    break
                if n>1 and delay>0:
                    self.log.info('waiting for {} seconds'.format(delay))
                    time.sleep(delay)
                    if self._abort():
                        break

                self.log.info('Record cycle {0}/{1}'.format(n,nCycles))
                self.log.info('Record dark upwelling spectra')
                for shutter in self._shutters:
                    self._shutters[shutter].closeShutter()
                for s in integrationTime['upwelling']:
                    self._spectrometers[s].acquire(milliseconds=integrationTime['upwelling'][s],dark=True,upwelling=True)
                # wait for all results
                self._wait()
                for s in integrationTime['upwelling']:
                    spectra.append(self._spectrometers[s].getSpectrum())
                # check if we should abort
                if self._abort():
                    break

                # record upwelling spectra
                self.log.info('Record upwelling spectra')
                self._shutters['upwelling'].openShutter()
                for s in integrationTime['upwelling']:
                    self._spectrometers[s].acquire(milliseconds=integrationTime['upwelling'][s],dark=False,upwelling=True)
                # wait for all results
                self._wait()
                for s in integrationTime['upwelling']:
                    spectra.append(self._spectrometers[s].getSpectrum())
                self._shutters['upwelling'].closeShutter()
                # check if we should abort
                if self._abort():
                    break

                # record downwelling spectra
                self.log.info('Record downwelling spectra')
                self._shutters['downwelling'].openShutter()
                for s in integrationTime['downwelling']:
                    self._spectrometers[s].acquire(milliseconds=integrationTime['downwelling'][s],dark=False,upwelling=False)
                # wait for all results
                self._wait()
                for s in integrationTime['downwelling']:
                    spectra.append(self._spectrometers[s].getSpectrum())
                self._shutters['downwelling'].closeShutter()
                # check if we should abort
                if self._abort():
                    break

                # record downwelling dark spectra
                self.log.info('Record dark upwelling spectra')
                for s in integrationTime['downwelling']:
                    self._spectrometers[s].acquire(milliseconds=integrationTime['downwelling'][s],dark=True,upwelling=False)
                # wait for all results
                self._wait()
                for s in integrationTime['downwelling']:
                    spectra.append(self._spectrometers[s].getSpectrum())

                self.log.info('finished acquisition {0}/{1}'.format(n,nCycles))
                self.results.put(spectra)


            if len(spectra)>0:
                self.results.put(spectra)
            self.busy.release()


class Piccolo(PiccoloInstrument):
    """piccolo server instrument

    the piccolo server itself is treated as an instrument"""

    def __init__(self,name,datadir,shutters,spectrometers):
        """
        :param name: name of the component
        :param datadir: data directory
        :type datadir: PiccoloDataDir
        :param shutters: dictionary of attached shutters
        :type shutters: dict(PiccoloShutter)
        :param spectrometers: dictionary of attached spectrometers
        :type spectrometers: dict(PiccoloSpectrometer)"""

        assert isinstance(datadir,PiccoloDataDir)
        PiccoloInstrument.__init__(self,name)
        self._datadir = datadir

        self._spectrometers = spectrometers.keys()
        self._spectrometers.sort()
        self._shutters = shutters.keys()
        self._shutters.sort()

        # integration times
        self._integrationTimes = {}
        for shutter in self.getShutterList():
            self._integrationTimes[shutter] = {}
            for spectrometer in self.getSpectrometerList():
                self._integrationTimes[shutter][spectrometer] = 1000

        # handling the worker thread
        self._busy = threading.Lock()
        self._tQ = Queue()
        self._rQ = Queue()
        self._worker = PiccoloThread(name,shutters,spectrometers,self._busy,self._tQ,self._rQ)
        self._worker.start()

    def getSpectrometerList(self):
        """get list of attached spectrometers"""
        return self._spectrometers

    def getShutterList(self):
        """return list of shutters"""
        return self._shutters

    def setIntegrationTime(self,shutter=None,spectrometer=None,milliseconds=1000.):
        """set the integration time

        :param shutter: the shutter name
        :param spectrometer: the spectrometer name
        :param milliseconds: the integration time in milliseconds"""
        if shutter not in self.getShutterList():
            return 'nok','unknown shutter: {}'.format(shutter)
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        self._integrationTimes[shutter][spectrometer] = milliseconds
        return 'ok'

    def getIntegrationTime(self,shutter=None,spectrometer=None):
        """get the integration time
        
        :param shutter: the shutter name
        :param spectrometer: the spectrometer name"""
        if shutter not in self.getShutterList():
            return 'nok','unknown shutter: {}'.format(shutter)
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        return self._integrationTimes[shutter][spectrometer]

    def record(self,delay=0.,nCycles=1):
        """record spectra

        :param delay: delay in seconds between each record
        :param nCycles: the number of recording cycles or 'Inf'"""

        if self._busy.locked():
            self.log.warning("already recording")
            return 'nok: already recording'
        self._tQ.put((self._integrationTimes,nCycles,delay))
        return 'ok'
    

    def abort(self):
        self._tQ.put('abort')

    def status(self):
        """return status of shutter

        :return: *busy* if recording or *idle*"""

        if self._busy.locked():
            return 'busy'
        else:
            return 'idle'


    def info(self):
        """get info

        :returns: dictionary containing system information
        :rtype: dict"""
        self.log.debug("info")
        info = {'hostname':  socket.gethostname(),
                'cpu_percent': psutil.cpu_percent(),
                'virtual_memory': dict(psutil.virtmem_usage()._asdict()),
                'status': self.status()}
        if self._datadir.isMounted:
            info['datadir'] = self._datadir.datadir
        else:
            info['datadir'] = 'not mounted'
        return info

    def getClock(self):
        """get the current date and time

        :returns: isoformat date and time string"""
        return datetime.datetime.now().isoformat()

    def setClock(self,clock=None):
        """set the current date and time

        :param clock: isoformat date and time string used to set the time"""
        if clock!=None:
            cmdPipe = subprocess.Popen(['sudo','date','-s',clock],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            if cmdPipe.wait()!=0:
                raise OSError, 'setting date to \'{}\': {}'.format(clock,cmdPipe.stderr.read())
            return cmdPipe.stdout.read()
        return ''
        
    def isMountedDataDir(self):
        """check if datadir is mounted"""
        return self._datadir.isMounted

    def mountDatadir(self):
        """attempt to mount datadir"""
        self._datadir.mount()
        return 'ok'

    def umountDatadir(self):
        """attempt to unmount datadir"""
        self._datadir.umount()
        return 'ok'


if __name__ == '__main__':
    from piccoloLogging import *

    piccoloLogging(debug=True)
    p = Piccolo("piccolo")
    print p.ping()
    print p.status()
    print p.info()
    print p.getClock()
