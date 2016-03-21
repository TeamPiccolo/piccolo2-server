"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['Piccolo']

from PiccoloInstrument import PiccoloInstrument
from PiccoloDataDir import PiccoloDataDir
from PiccoloWorkerThread import PiccoloWorkerThread
from PiccoloSpectrometer import PiccoloSpectraList
import socket
import psutil
import subprocess
import datetime
import threading
from Queue import Queue, Empty
import time
import logging
import os.path

class PiccoloThread(PiccoloWorkerThread):
    """worker thread handling a number of shutters and spectrometers"""

    LOGNAME = 'piccolo'

    def __init__(self,name,shutters,spectrometers,busy,paused,tasks,results):

        PiccoloWorkerThread.__init__(self,name,busy,tasks,results)
        
        self._paused = paused
        self._shutters = shutters
        self._spectrometers = spectrometers
        self._outCounter = {}

    def _wait(self):
        time.sleep(0.2)

    def _getCommands(self,block=True):
        try:
            cmd = self.tasks.get(block=block)
        except Empty:
            return
        
        self.log.debug(cmd)

        if cmd == None:
            self.log.info('shutting down')
            return 'shutdown'
        elif cmd == 'abort':
            if self.busy.locked():
                self.log.info('aborted acquisition')
                return 'abort'
            else:
                self.log.warn('abort called but not busy')
                return
        elif cmd == 'pause':
            if self._paused.locked():
                # unpause acquisition
                self.log.info('unpause acquisition')
                self._paused.release()
                return 'unpause'
            else:
                # pause acquisition
                self.log.info('pause acquisition')
                self._paused.acquire()
                # wait for a new command
                while True:
                    cmd = self._getCommands()
                    if cmd in ['shutdown','abort']:
                        self._paused.release()
                        return cmd
                    elif cmd == 'unpause':
                        return
                    else:
                        self.log.warn('acquisition paused')

        else:
            assert len(cmd)==4
            if self.busy.locked():
                self.log.warn('already recording data')
                return
            return cmd
        
    def getCounter(self,key):
        if key not in self._outCounter:
            self._outCounter[key] = 0
        else:
            self._outCounter[key] += 1
        return self._outCounter[key]

    def run(self):
        while True:
            # wait for a new task from the task queue
            task = self._getCommands()
            if task == None:
                continue
            elif task == 'shutdown':
                return
            elif len(task) == 4:
                # get task
                (integrationTime,outDir,nCycles,delay) = task
            else:
                # nothing interesting, get the next command
                continue

            # start recording
            self.log.info("start recording {}".format(nCycles))
            self.busy.acquire()

            n = 0
            prefix = os.path.join(outDir,'{0:04d}_'.format(self.getCounter(outDir)))
            while True:
                spectra = PiccoloSpectraList(seqNr=n)
                spectra.prefix = prefix
                n = n+1
                if nCycles!='Inf' and n > nCycles:
                    break
                if n>1 and delay>0:
                    self.log.info('waiting for {} seconds'.format(delay))
                    time.sleep(delay)
                    # check for abort/shutdown
                    cmd = self._getCommands(block=False)
                    if cmd=='abort':
                        break
                    elif cmd=='shutdown':
                        return

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
                # check for abort/shutdown
                cmd = self._getCommands(block=False)
                if cmd=='abort':
                    break
                elif cmd=='shutdown':
                    return

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
                # check for abort/shutdown
                cmd = self._getCommands(block=False)
                if cmd=='abort':
                    break
                elif cmd=='shutdown':
                    return

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
                # check for abort/shutdown
                cmd = self._getCommands(block=False)
                if cmd=='abort':
                    break
                elif cmd=='shutdown':
                    return

                # record downwelling dark spectra
                self.log.info('Record dark upwelling spectra')
                for s in integrationTime['downwelling']:
                    self._spectrometers[s].acquire(milliseconds=integrationTime['downwelling'][s],dark=True,upwelling=False)
                # wait for all results
                self._wait()
                for s in integrationTime['downwelling']:
                    spectra.append(self._spectrometers[s].getSpectrum())

                self.results.put(spectra)
                self.log.info('finished acquisition {0}/{1}'.format(n,nCycles))

            self.busy.release()

class PiccoloOutput(threading.Thread):
    """piccolo writer thread"""

    def __init__(self,name,datadir,spectra,clobber=True,daemon=True):
        assert isinstance(spectra,Queue)
        
        threading.Thread.__init__(self)
        self.name = name
        self.daemon = daemon

        self._log = logging.getLogger('piccolo.worker.output.{0}'.format(name))
        self.log.info('initialising worker')

        self._spectraQ = spectra
        self._datadir = datadir
        self._clobber = clobber

    @property
    def log(self):
        return self._log

    def run(self):
        while True:
            spectra = self._spectraQ.get()
            if spectra == None:
                self.log.info('shutting down')
                return

            self.log.info('writing {} to {}'.format(self._datadir.datadir,spectra.outName))
            spectra.write(prefix=self._datadir.datadir,clobber=self._clobber)
            

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
        self._paused = threading.Lock()
        self._tQ = Queue()
        self._rQ = Queue()
        self._worker = PiccoloThread(name,shutters,spectrometers,self._busy,self._paused,self._tQ,self._rQ)
        self._worker.start()

        # handling the output thread
        self._output = PiccoloOutput(name,self._datadir,self._rQ)
        self._output.start()

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

    def record(self,outDir='spectra',delay=0.,nCycles=1):
        """record spectra

        :param outDir: name of output directory
        :param delay: delay in seconds between each record
        :param nCycles: the number of recording cycles or 'Inf'"""

        if self._busy.locked():
            self.log.warning("already recording")
            return 'nok: already recording'
        self._tQ.put((self._integrationTimes,outDir,nCycles,delay))
        return 'ok'
    

    def abort(self):
        self._tQ.put('abort')

    def pause(self):
        self._tQ.put('pause')

    def status(self):
        """return status of shutter

        :return: (busy,paused) 
        :rtype:  (bool, bool)"""

        busy = self._busy.locked()
        paused = self._paused.locked()

        return (busy,paused)

    def info(self):
        """get info

        :returns: dictionary containing system information
        :rtype: dict"""
        self.log.debug("info")

        status = self.status()
        if status[0]:
            s = 'busy'
        else:
            s = 'idle'
        if status[1]:
            s += ', paused'

        info = {'hostname':  socket.gethostname(),
                'cpu_percent': psutil.cpu_percent(),
                'virtual_memory': dict(psutil.virtmem_usage()._asdict()),
                'status': s}
        if self._datadir.isMounted:
            info['datadir'] = self._datadir.datadir
        else:
            info['datadir'] = 'not mounted'
        return info

    def getSpectraList(self,outDir='spectra'):
        return self._datadir.getFileList(outDir)

    def getSpectra(self,fname=''):
        return self._datadir.getFileData(fname)

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
