# Copyright 2014-2016 The Piccolo Team
#
# This file is part of piccolo2-server.
#
# piccolo2-server is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# piccolo2-server is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with piccolo2-server.  If not, see <http://www.gnu.org/licenses/>.

"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['Piccolo']

from PiccoloInstrument import PiccoloInstrument
from PiccoloDataDir import PiccoloDataDir
from PiccoloWorkerThread import PiccoloWorkerThread
from PiccoloSpectrometer import PiccoloSpectraList
from PiccoloMessages import PiccoloMessages
from piccolo2.PiccoloStatus import PiccoloStatus, PiccoloExtendedStatus
import PiccoloSimplify
import socket
import psutil
import subprocess
import datetime
import threading
from Queue import Queue, Empty
import time
import logging
import os.path, json
import numpy
import math

class IntegrationTimes(object):
    def __init__(self,shutters,spectrometers,callback=None):
        self._shutters = shutters
        self._spectrometers = spectrometers
        self._integrationTime = {}
        self._integrationTimeSource = {}
        for shutter in self.shutters:
            self._integrationTime[shutter] = {}
            self._integrationTimeSource[shutter] = {}
            for spec in self.spectrometers:
                self._integrationTime[shutter][spec] = -1
                self._integrationTimeSource[shutter][spec] = 0
        self._callback = callback

    @property
    def shutters(self):
        return self._shutters
    @property
    def spectrometers(self):
        return self._spectrometers

    def setTime(self,shutter,spectrometer,t,source=0):
        changed=False
        if abs(self._integrationTime[shutter][spectrometer] - t) > 1e-8:
            changed = True
            self._integrationTime[shutter][spectrometer] = t
        if source != self._integrationTimeSource[shutter][spectrometer]:
            changed = True
            self._integrationTimeSource[shutter][spectrometer] = source
        if self._callback is not None and changed:
            self._callback(shutter,spectrometer,t,source)

    def setSource(self,shutter,spectrometer,source):
        if source != self._integrationTimeSource[shutter][spectrometer]:
            self._integrationTimeSource[shutter][spectrometer] = source
            if self._callback is not None:
                self._callback(shutter,spectrometer,self.getTime(shutter,spectrometer),source)
            
    def getTime(self,shutter,spectrometer):
        return self._integrationTime[shutter][spectrometer]

    def getSource(self,shutter,spectrometer):
        return self._integrationTimeSource[shutter][spectrometer]

    def allChanged(self):
        if self._callback is not None:
            for shutter in self.shutters:
                for spectrometer in self.spectrometers:
                    self._callback(shutter,spectrometer,self.getTime(shutter,spectrometer),self.getSource(shutter,spectrometer))
    
class PiccoloThread(PiccoloWorkerThread):
    """worker thread handling a number of shutters and spectrometers"""

    LOGNAME = 'piccolo'

    def __init__(self,name,datadir,shutters,spectrometers,gps,busy,paused,tasks,results,stateChanges,file_incremented):

        PiccoloWorkerThread.__init__(self,name,busy,tasks,results)

        self._datadir = datadir
        self._paused = paused
        self._shutters = shutters
        self._spectrometers = spectrometers
        self._outCounter = {}
        self._integrationTimes = IntegrationTimes(self._shutters.keys(),self._spectrometers.keys(),callback=self._itChanged)
        self._needDark = False
        self._auto = -1
        self._currentRun = 'spectra'
        self._nCycles = 1
        self._delay = 0
        self._stateChanges = stateChanges
        self._file_incremented = file_incremented

        # populate integration times object
        for shutter in shutters.keys():
            for spectrometer in self._spectrometers.keys():
                self._integrationTimes.setTime(shutter,spectrometer,self._spectrometers[spectrometer].getCurrentIntegrationTime())

    def openShutter(self,shutter):
        self._shutters[shutter].openShutter()
        self._stateChanges.put(('o',shutter))
    def closeShutter(self,shutter):
        self._shutters[shutter].closeShutter()
        self._stateChanges.put(('c',shutter))

    def _itChanged(self,shutter,spectrometer,t,s):
        self._stateChanges.put(('t',shutter,spectrometer,t,s))
        
    def setIntegrationTime(self,shutter,spectrometer,milliseconds,roundup=True,source=0):
        v = float(milliseconds)
        if roundup:
            n = 10**(math.floor(math.log10(v))-1)
            if v/n>v//n:
                v = (v//n+1)*n
        v = max(v,self._spectrometers[spectrometer].getMinIntegrationTime())
        v = min(v,self._spectrometers[spectrometer].getMaxIntegrationTime())
        if abs(v - self._integrationTimes.getTime(shutter,spectrometer)) > 1e-8:
            self._needDark = True
        self._integrationTimes.setTime(shutter,spectrometer,v,source)
    def getAllIntegrationTimes(self):
        self._integrationTimes.allChanged()

    def getAuto(self):
        self._stateChanges.put(('ai',self._auto))        
    def setAuto(self,auto):
        try:
            a = int(auto)
        except:
            logging.error('cannot set auto to %s'%str(auto))
            return
        if a != self._auto:
            self._auto = a
            self.getAuto()

    def getCurrentRun(self):
        self._stateChanges.put(('cr',self._currentRun))
    def setCurrentRun(self,cr):
        if cr != self._currentRun:
            self._currentRun = cr
            self.currentRun()

    def getNCycles(self):
        self._stateChanges.put(('nc',self._nCycles))
    def setNCycles(self,nCycles):
        try:
            n = int(nCycles)
            assert n>=0
        except:
            logging.error('cannot set nCycles to %s'%str(nCycles))
            return
        if n != self._nCycles:
            self._nCycles = n
            self.getNCycles()

    def getDelay(self):
        self._stateChanges.put(('d',self._delay))
    def setDelay(self,delay):
        try:
            d = float(delay)
            assert d>=0.
        except:
            logging.error('cannot set delay to %s'%str(delay))
            return
        if d != self._delay:
            self._delay = d
            self.getDelay()
        
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
        elif cmd =='dark':
            return cmd
        elif cmd == 'getTimes':
            self.getAllIntegrationTimes()
        elif cmd == 'getCurrentRun':
            self.getCurrentRun()
        elif cmd == 'getNCycles':
            self.getNCycles()
        elif cmd == 'getDelay':
            self.getDelay()
        elif cmd == 'getAuto':
            self.getAuto()
        elif cmd == 'auto':
            if self.busy.locked():
                self.log.warn('already recording data')
                return
            return cmd
        elif cmd[0] in ['setMinTime','setMaxTime','setCurrentRun','setNCycles','setDelay','setAuto']:
            return cmd    
        else:
            if self.busy.locked():
                self.log.warn('already recording data')
                return
            return cmd

    def setMinIntegrationTime(self,spectrometer,milliseconds):
        self._spectrometers[spectrometer].setMinIntegrationTime(milliseconds)

    def setMaxIntegrationTime(self,spectrometer,milliseconds):
        self._spectrometers[spectrometer].setMaxIntegrationTime(milliseconds)
        
    def getCounter(self,key):
        if key not in self._outCounter:
            self._outCounter[key] = self._datadir.getNextCounter(key)
            if self._outCounter[key] > 0:
                self.log.warn('spectra index set to %d'%self._outCounter[key])
                self._file_incremented.set()
            else:
                self._file_incremented.clear()
        else:
            self._outCounter[key] += 1
        return self._outCounter[key]

    def autoIntegrate(self):
        # close all shutters
        self._stateChanges.put(('a','start'))
        for shutter in self._shutters:
            self.closeShutter(shutter)
        for shutter in self._shutters:
            self.openShutter(shutter)
            # start autointegration
            for s in self._spectrometers:
                self._spectrometers[s].autointegrate()
            self._wait()
            # get results
            for s in self._spectrometers:
                r=self._spectrometers[s].getAutointegrateResult()
                self._stateChanges.put(('a',shutter,s,r.success))
                if r.success:
                    self.setIntegrationTime(shutter,s,r.bestIntegrationTime,source=1)
                else:
                    self._integrationTimes.setSource(shutter,s,source=2) # indicate that the autointegration failed
            self.closeShutter(shutter)
        self._stateChanges.put(('a','stop'))

    def record(self,shutter,dark=False):
        self._stateChanges.put(('r','start'))
        if dark:
            darkStr = 'dark'
        else:
            darkStr = 'light'
        self.log.info("Record {0} {1} spectra".format(darkStr,shutter))

        # open/close shutters as required
        for s in self._shutters:
            if not dark and s == shutter:
                self.openShutter(s)
            else:
                self.closeShutter(s)

        for s in self._integrationTimes.spectrometers:
            self._spectrometers[s].acquire(milliseconds=self._integrationTimes.getTime(shutter,s),dark=dark,shutter=shutter)

        self._wait()
        spectra = []
        for s in self._integrationTimes.spectrometers:
            spectra.append(self._spectrometers[s].getSpectrum())

        self.closeShutter(shutter)
        self._stateChanges.put(('r','stop'))
        return spectra

    def run(self):
        while True:
            # wait for a new task from the task queue
            task = self._getCommands()
            if task == None:
                continue
            elif task == 'shutdown':
                return
            elif task == 'auto':
                self.log.info("start autointegration")
                self.busy.acquire()
                self.autoIntegrate()
                self.busy.release()
                self.log.info("finished autointegration")
                continue
            elif task[0] ==  'setMinTime':
                self.setMinIntegrationTime(task[1],task[2])
                continue
            elif task[0] == 'setMaxTime':
                self.setMaxIntegrationTime(task[1],task[2])
                continue
            elif task[0] == 'setTime':
                self.setIntegrationTime(task[1],task[2],task[3],source=0)
                continue
            elif task[0] == 'setCurrentRun':
                self.setCurrentRun(task[1])
                continue
            elif task[0] == 'setNCycles':
                self.setNCycles(task[1])
                continue
            elif task[0] == 'setDelay':
                self.setDelay(task[1])
                continue
            elif task[0] == 'setAuto':
                self.setAuto(task[1])
                continue
            elif task[0] == 'record':
                # get task
                (outDir,nCycles,delay) = task[1:]
            else:
                # nothing interesting, get the next command
                continue

            # start recording
            self.log.info("start recording {}".format(nCycles))
            self.busy.acquire() # Lock the Piccolo thread, to prevent recording whilst already recording.

            # run initial autointegration if requested
            if self._auto == 0:
                self.log.info("start autointegration")
                self.autoIntegrate()
                self.log.info("finished autointegration")
            
            n = 0 # n is the sequence number. The first sequence is 0, the last is nCycles-1.
            # Work out the output filename.
            batchNr = self.getCounter(outDir)
            prefix = os.path.join(outDir,'b{0:06d}_s'.format(batchNr))
            while True:
                spectra = PiccoloSpectraList(seqNr=n)
                spectra.prefix = prefix
                cmd = None
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
                    elif cmd=='dark':
                        self._needDark = True

                self.log.info('Record cycle {0}/{1}'.format(n,nCycles))

                if self._auto>0 and (n-1)%self._auto==0:
                    self.log.info("start autointegration")
                    self.autoIntegrate()
                    self.log.info("finished autointegration")

                
                # order of dark/light measurements
                # * the first sequence of a batch or when a dark measurement is required is dark
                # * then do a light measurement
                # * if it is the last sequence in a batch record a dark measurement
                # ** but if the first measurement is already a dark one swap measurements
                #
                # so at most two measurements are taken (one dark and one light)
                measurements = []
                if n==1 or self._needDark:
                    measurements.append(True) 
                measurements.append(False)
                if n==nCycles:
                    if not measurements[0]:
                        measurements.append(True)
                    else:
                        measurements.reverse()

                # loop over measurements
                for dark in measurements:
                    for shutter in self._shutters:
                        for s in self.record(shutter,dark):
                            # Insert the batch and sequence numbers into the metadata.
                            s.update({'Batch': batchNr,'Run':outDir})
                            spectra.append(s)
                        # check for abort/shutdown
                        cmd = self._getCommands(block=False)
                    if dark:
                        self._needDark = False
                    if cmd in ['abort','shutdown']:
                        break

                if cmd=='abort':
                    break
                elif cmd=='shutdown':
                    return

                self.results.put(spectra)
                self.log.info('finished acquisition {0}/{1}'.format(n,nCycles))

            self.busy.release()

class PiccoloOutput(threading.Thread):
    """piccolo writer thread"""

    def __init__(self,name,datadir,spectra,clobber=True,daemon=True,split=True):
        assert isinstance(spectra,Queue)

        threading.Thread.__init__(self)
        self.name = name
        self.daemon = daemon

        self._log = logging.getLogger('piccolo.worker.output.{0}'.format(name))
        self.log.info('initialising worker')

        self._spectraQ = spectra
        self._datadir = datadir
        self._clobber = clobber
        self._split = split

    @property
    def log(self):
        return self._log

    def run(self):
        while True:
            spectra = self._spectraQ.get()
            if spectra == None:
                self.log.info('shutting down')
                return

            self.log.info('writing {} to {}'.format(spectra.outName,self._datadir.datadir))
            try:
                spectra.write(prefix=self._datadir.datadir,clobber=self._clobber,split=self._split)
            except RuntimeError, e:
                self.log.error('writing {} to {}: {}'.format(spectra.outName,self._datadir.datadir,e))


class Piccolo(PiccoloInstrument):
    """piccolo server instrument

    the piccolo server itself is treated as an instrument"""

    def __init__(self,name,datadir,shutters,spectrometers,gps,clobber=True,split=True,cfg={}):
        """
        :param name: name of the component
        :param datadir: data directory
        :type datadir: PiccoloDataDir
        :param shutters: dictionary of attached shutters
        :type shutters: dict(PiccoloShutter)
        :param spectrometers: dictionary of attached spectrometers
        :type spectrometers: dict(PiccoloSpectrometer)
        :param clobber: overwrite exciting files when set to True
        :param split: split files into dark and light spectra when set to True"""

        assert isinstance(datadir,PiccoloDataDir)
        PiccoloInstrument.__init__(self,name)
        self._datadir = datadir

        self._spectraCache = (None,None)

        self._spectrometers = spectrometers.keys()
        self._spectrometers.sort()
        self._shutters = shutters.keys()
        self._shutters.sort()

        self._status = PiccoloStatus()
        self._status.connected = True

        self._gps = gps

        self._cfg = cfg

        self._messages = PiccoloMessages()

        # the record parameters
        try:
            self._currentRun = self._datadir.getRunList()[-1]
        except:
            self._currentRun = 'spectra'
        self._auto = -1
        self._nCycles = 1
        self._delay = 0
            
        # the extended status
        self._extendedStatus = PiccoloExtendedStatus(spectrometers.keys(),shutters.keys())
            
        # integration times
        self._integrationTimes = IntegrationTimes(self.getShutterList(),self.getSpectrometerList(),callback=self._itChanged)
        self._minIntegrationTimes = {}
        self._maxIntegrationTimes = {}
        for spectrometer in self.getSpectrometerList():
            self._minIntegrationTimes[spectrometer] = spectrometers[spectrometer].getMinIntegrationTime()
            self._maxIntegrationTimes[spectrometer] = spectrometers[spectrometer].getMaxIntegrationTime()

        # handling the worker thread
        self._busy = threading.Lock()
        self._paused = threading.Lock()
        self._tQ = Queue()
        self._rQ = Queue()
        self._sQ = Queue()
        self._file_incremented = threading.Event()
        self._worker = PiccoloThread(name,self._datadir,shutters,spectrometers, gps, self._busy,self._paused,self._tQ,self._rQ, self._sQ,self._file_incremented)
        self._worker.start()

        # handling the output thread
        self._output = PiccoloOutput(name,self._datadir,self._rQ,clobber=clobber,split=split)
        self._output.start()

        # update the integration times
        self._tQ.put("getTimes")

    def _itChanged(self,shutter,spectrometer,t,s):
        self._messages.addMessage('IT|%s|%s'%(spectrometer,shutter))

    def _paramChanged(self,param,value,key=None):
        p = '_'+param
        if getattr(self,p) != value:
            setattr(self,p,value)
            if key is not None:
                self._messages.addMessage('{}|{}'.format(key,value))
        
    def getListenerID(self):
        """get a listener ID for use with messages"""
        return self._messages.newListener()

    def removeListener(self,listener=None):
        """remove a listener"""
        try:
            self._messages.removeListener(listener)
        except:
            self.log.warning('could not remove listener %s'%str(listener))

    def getMessage(self,listener=None):
        """get a message"""
        return self._messages.getMessage(listener)

    def getSpectrometerList(self):
        """get list of attached spectrometers"""
        return self._spectrometers

    def getShutterList(self):
        """return list of shutters"""
        return self._shutters
    
    def setIntegrationTime(self,shutter=None,spectrometer=None,milliseconds=1000.):
        """Set the integration time manually.

        Integration times can be adjusted for each direction (upwelling and
        downwelling) and each spectrometer. On Piccolo instruments with
        one spectrometer, there are two separate integration times: upwelling
        and downwelling. On Piccolo instruments with two spectrometers, there
        will be four integration times (two spectrometers times two directions).

        Dark spectra are recorded at the same integration time as their
        corresponding light spectra.

        This functions sets the integration times manually. An alternative is to
        set them automatically.

        :param shutter: the shutter name ("direction"), 'upwelling' or 'downwelling'
        :param spectrometer: the spectrometer name
        :param milliseconds: the integration time in milliseconds"""
        if shutter not in self.getShutterList():
            return 'nok','unknown shutter: {}'.format(shutter)
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        self._tQ.put(("setTime",shutter,spectrometer,milliseconds))
        return 'ok'

    def setMinIntegrationTime(self,spectrometer=None,milliseconds=1000.):
        """set the minimum integration time"""
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        self._messages.addMessage('ITmin|%s'%(spectrometer))
        self._minIntegrationTimes[spectrometer] = milliseconds
        self._worker.setMinIntegrationTime(spectrometer,milliseconds)
        return 'ok'
    
    def setMaxIntegrationTime(self,spectrometer=None,milliseconds=1000.):
        """set the maximum integration time"""
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        self._messages.addMessage('ITmax|%s'%(spectrometer))
        self._maxIntegrationTimes[spectrometer] = milliseconds
        self._worker.setMaxIntegrationTime(spectrometer,milliseconds)
        return 'ok'
    
    def setIntegrationTimeManual(self, shutter=None, spectrometer=None, milliseconds=1000.):
        """Set the integration time manually.

        See description of the setIntegrationTime function.
        """
        self.setIntegrationTime(shutter, spectrometer, milliseconds)

    def setIntegrationTimeAuto(self):
        """Sets the integration time automatically.

        The max parameter is the maximum integration time (in milliseconds)
        which may be set on the spectrometer. Autointegration will never
        return an integration time longer than this. If it is not possible to
        find an integration time less than max, then an error will occur and
        autointegration will fail.

        :param max: the maximum integration time in milliseconds
        """

        if self._busy.locked():
            self.log.warning("already recording")
            return 'nok: already recording'
        self._tQ.put('auto')
        return 'ok'

    def getIntegrationTime(self,shutter=None,spectrometer=None):
        """get the integration time

        :param shutter: the shutter name
        :param spectrometer: the spectrometer name"""
        if shutter not in self.getShutterList():
            return 'nok','unknown shutter: {}'.format(shutter)
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        return self._integrationTimes.getTime(shutter,spectrometer)

    def getIntegrationTimeSource(self,shutter=None,spectrometer=None):
        """get the source of integration time

        :param shutter: the shutter name
        :param spectrometer: the spectrometer name"""
        if shutter not in self.getShutterList():
            return 'nok','unknown shutter: {}'.format(shutter)
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        return self._integrationTimes.getSource(shutter,spectrometer)
    
    def getMinIntegrationTime(self,spectrometer=None):
        """get the minimum integration time

        :param spectrometer: the spectrometer name"""
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        return self._minIntegrationTimes[spectrometer]
    
    def getMaxIntegrationTime(self,spectrometer=None):
        """get the maximum integration time

        :param spectrometer: the spectrometer name"""
        if spectrometer not in self.getSpectrometerList():
            return 'nok', 'unknown spectrometer: {}'.format(spectrometer)
        return self._maxIntegrationTimes[spectrometer]

    def setAuto(self,auto):
        """set autointegration

        :param auto: integer, can be -1 for never; 0 once at the beginning; otherwise every nth measurement
        """
        self._tQ.put(('setAuto',auto))
        return 'ok'
    def getAuto(self):
        """get the current autointegration value"""
        self.status()
        return self._auto
        
    def record(self,outDir='spectra',delay=0.,nCycles=1,timeout=30.):
        """record spectra

        :param outDir: name of output directory
        :param delay: delay in seconds between each record
        :param nCycles: the number of recording cycles or 'Inf'
        :param timeout: wait at most timeoutseconds for autointegration to have finished"""

        if self._busy.locked():
            self.log.warning("already recording")
            return 'nok: already recording'
        if outDir != self._currentRun:
            self._currentRun = outDir
            self._messages.addMessage('CR|%s'%outDir)
        self._tQ.put(('record',outDir,nCycles,delay))
        return 'ok'

    def dark(self):
        """record a dark spectrum"""
        if not self._busy.locked():
            self.log.warning("not recording")
            return 'nok: not recording'
        self._tQ.put('dark')
        return 'ok'

    def abort(self):
        self._tQ.put('abort')

    def pause(self):
        self._tQ.put('pause')

    def status(self,listener=None):
        """return status of shutter

        :return: (busy,paused)
        :rtype:  (bool, bool)"""


        # check if there are any state changes
        while True:
            try:
                sc = self._sQ.get(block=False)
            except Empty:
                break

            if sc[0] == 't':
                shutter,spectrometer,milliseconds,source = sc[1:]
                self._integrationTimes.setTime(shutter,spectrometer,milliseconds,source)
            elif sc[0] == 'o':
                self._extendedStatus.open(sc[1])
            elif sc[0] == 'c':
                self._extendedStatus.close(sc[1])
            elif sc[0] == 'ai':
                self._paramChanged('auto',sc[1],'AI')
            elif sc[0] == 'cr':
                self._paramChanged('currentRun',sc[1],'CR')
            elif sc[0] == 'nc':
                self._paramChanged('nCycles',sc[1],'NC')
            elif sc[0] == 'd':
                self._paramChanged('delay',sc[1],'D')
            elif sc[0] == 'r':
                if sc[1] == 'start':
                    self._extendedStatus.start_recording()
                elif sc[1] == 'stop':
                    self._extendedStatus.stop_recording()
            elif sc[0] == 'a':
                if sc[1] == 'start':
                    self._extendedStatus.start_autointegration()
                elif sc[1] == 'stop':
                    self._extendedStatus.stop_autointegration()
                else:
                    shutter,spectrometer,result = sc[1:]
                    self._extendedStatus.setAutointegrationResult(spectrometer,shutter,result)

        self._status.busy = self._busy.locked()
        self._status.paused = self._paused.locked()
        self._status.file_incremented = self._file_incremented.isSet()

        if self._status.file_incremented:
            self._messages.warning("avoided overwriting existing file by incrementing file number")
            self._file_incremented.clear()

        try:
            self._status.new_message = self._messages.status(listener)
        except:
            self._status.new_message = False

        return self._status.encode(),self._extendedStatus.encode()

    def info(self):
        """get info

        :returns: dictionary containing system information
        :rtype: dict"""
        self.log.debug("info")

        status = self.status()
        if status[0][0]:
            s = 'busy'
        else:
            s = 'idle'
        if status[1]:
            s += ', paused'

        info = {'hostname':  socket.gethostname(),
                'cpu_percent': psutil.cpu_percent(),
                'status': s}
        if self._datadir.isMounted:
            info['datadir'] = self._datadir.datadir
        else:
            info['datadir'] = 'not mounted'
        return info

    def getSpectraList(self,outDir='spectra',haveNFiles=0):
        return self._datadir.getFileList(outDir,haveNFiles=haveNFiles)

    def getSpectra(self,fname='',chunk=None):
        data = self._datadir.getFileData(fname)
        if chunk == None:
            return data
        else:
            if fname != self._spectraCache[0]:
                if 'SimplifySpectra' in self._cfg:
                    self.log.info("SimplifySpectra")
                    data = self.simplifySpectra(data)

                self._spectraCache = (fname,PiccoloSpectraList(data=data))
            return self._spectraCache[1].getChunk(chunk)

    def simplifySpectra(self, data):
        jdata = json.loads(data)

        piccoloData = {
            "SequenceNumber": jdata['SequenceNumber'],
            "Spectra": jdata['Spectra']
        }

        for s in piccoloData['Spectra']:
            meta            = s['Metadata']
            pixels          = s['Pixels']
            serialNumber    = meta['SerialNumber']
            dark            = meta['Dark']
            direction       = meta["Direction"]

            WavelengthCalibrationCoefficients = meta['WavelengthCalibrationCoefficients']
            wcc = WavelengthCalibrationCoefficients

            s['Pixels'] = numpy.asarray(s['Pixels'],dtype=numpy.float32)
            isize = s['Pixels'].size
            wavelengths = numpy.poly1d(wcc[::-1])(numpy.arange(s['Pixels'].size))
            threshold = 10
            if "QEP" in serialNumber:
                self.log.info("Using lower simplification threshold for {0}".format(serialNumber))
                threshold=2

            simple_px,simple_wv = PiccoloSimplify.simplify(s['Pixels'],wavelengths,threshold)
            simple_px = numpy.round(simple_px,2).tolist()

            s['Metadata']['Wavelengths'] = numpy.round(simple_wv,3).tolist()
            del s['Metadata']['WavelengthCalibrationCoefficients']
            s['Pixels'] = numpy.round(simple_px,2).tolist()
            print(len(s['Pixels']))
            print(len(s['Metadata']['Wavelengths']))
            osize = len(s['Pixels'])

            self.log.info("Simplified {0} {1} {2} from {3} pts to {4} pts".format(serialNumber, direction, dark, isize, osize))

        return piccoloData

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

    def getRunList(self):
        """get a list of all runs"""
        return self._datadir.getRunList()
    
    def getCurrentRun(self):
        """get the name of the current run directory"""
        return self._currentRun
    
    def getLocation(self):
        """get current GPS location and metadata"""
        return self._gps.getRecord()

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
