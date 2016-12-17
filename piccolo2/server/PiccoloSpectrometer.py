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
.. moduleauthor:: Iain Robinson <iain@physics.org>
"""

__all__ = ['PiccoloSpectrometer']

from piccolo2.PiccoloSpectra import *
from PiccoloInstrument import PiccoloInstrument
from PiccoloWorkerThread import PiccoloWorkerThread
import time
import threading
from Queue import Queue
import logging

class Task(object):
    pass

class AcquireTask(Task):
    """Class to hold instructions for acquiring a spectrum.

    The instructions tell the spectrometer to acquire a spectrum at a specified
    integration time. The direction must also be specified to tell the
    spectrometer which shutter to open. If the spectrum is specified to be a
    dark spectrum, the shutter is closed during the acquisition.
    """

    def init(self):
        self._direction = None # Can be 'upwelling' or 'downwelling'. No default.
        self._integrationTime = None # milliseconds. No default.
        self._dark = False # True if dark, False if light. Default: False.

    @property
    def direction(self):
        """Returns the direction as a string.

        :returns:  str -- "upwelling" or "downwelling".
        """
        if self._direction is None:
            raise Exception('The direction (upwelling or downwelling) of the spectrum to be acquired has not been specified.')
        return self._direction

    @direction.setter
    def direction(self, newDirection):
        """Set the (optical) direction of the spectrum to be acquired.

        This is the direction which light entering the spectrometer originiates
        from. The allowed directions are "upwelling" and "downwelling". The
        downwelling direction is typically used to acquire a spectrum of light
        travelling downwards from the sky. The upwelling direction is typically
        used to acquire a spectrum of light reflected from the ground, i.e. the
        light is travelling upwards.

        :param newDirection: 'upwelling' or 'downwelling'
        :type newDirection: str
        """

        newDirectionLowerCase = newDirection.lower()
        if newDirectionLowerCase != 'upwelling' and newDirectionLowerCase != 'downwelling':
            raise TypeError('The Piccolo supports only two directions: "downwelling" and "upwelling". The direction "{}" is not supported.'.format(newDirection))
        self._direction = newDirectionLowerCase

    @property
    def integrationTime(self):
        if self._integrationTime is None:
            raise Exception('The integration time of the spectrum to be acquired has not been specified.')
        return self._integrationTime

    @integrationTime.setter
    def integrationTime(self, t):
        """Set the integration time at which the spectrum will be acquired.

        :param t: the integration time in milliseconds.
        :type t: float
        """
        tFloat = None
        try:
            tFloat = float(t)
        except TypeError:
            raise TypeError('The integration time must be a number. {} is not a number, it is {}.'.format(t, type(t)))
        if tFloat < 0:
            raise Exception('The integraiton time ({} ms) cannot be negative.'.format(tFloat))
        self._integrationTime = t

    @property
    def dark(self):
        """Returns True is the spectrum is a dark spectrum, False otherwise."""
        if self._dark is None:
            raise Exception('It has not been specified as to whether the spectrum to be acquired is a dark spectrum.')
        return self._dark

    @dark.setter
    def dark(self, isDark):
        """Set to True if a dark spectrum is to be acquired.

        By default, a light spectrum will be acquired. It is therefore only
        necessary to set dark to True when preparing a task to acquire a dark
        spectrum.

        :param isDark: True if the spectrum is dark, false if it is light.
        :type isDark: bool
        """
        if not isinstance(isDark, bool):
            raise TypeError("Dark must be True or False. {} is {}.".format(isDark, type(isDark)))
        self._dark = isDark

class AutointegrateTask(Task):
    """Class to represent a request for an autointegration.

    The autointegration task is used to prepare a spectrometer autointegration.

    Two parameters must be provided:

    1. How close should the spectrum be to saturation?
    2. What's the longest integration time that would be acceptable?

    The first of these could be specified as a percentage of the spectrometer's
    saturation level. A value of 70 per cent would be typical and allow space
    for any fluctuation in the light level during the acquisition of a batch.

    The second parameter should default to the maximum integration time
    supported by the spectrometer. There is likely to be a user-specified
    maximum integration time at which spectra will be acquired. Longer than this
    and spectra are too noisy to be used.
    """

    pass # Not implemented yet.

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
            self.log.info("start recording for {} milliseconds".format(task.integrationTime))
            self.busy.acquire()

            # create new spectrum instance
            spectrum = PiccoloSpectrum()
            spectrum.setDark(task.dark)
            if task.direction == 'upwelling':
                spectrum.setUpwelling(True)
            elif task.direction == 'downwelling':
                spectrum.setUpwelling(False)
            else:
                raise Exception('Unsupported direction: "{}"'.format(task.direction))
            spectrum['name'] = self.name

            # record data
            if self._spec==None:
                time.sleep(task.integrationTime/1000.)
                pixels = [1]*100
            else:
                self._spec.setIntegrationTime(task.integrationTime)
                spectrum.update(self._spec.getMetadata())
                self._spec.requestSpectrum()
                pixels = self._spec.readSpectrum()

            spectrum.pixels = pixels

            # write results to the result queue
            self.results.put(spectrum)
            self.busy.release()

class PiccoloSpectrometer(PiccoloInstrument):
    """Class to communicate with a spectrometer."""

    def __init__(self,name,spectrometer=None):

        PiccoloInstrument.__init__(self,name)

        # The lock prevents two threads using the spectrometer at the same time.
        self._busy = threading.Lock()
        self._tQ = Queue() # Task queue.
        self._rQ = Queue() # Results queue.

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

        :returns: dictionary containing information about the spectrometer
        :rtype: dict"""

        return {'serial' : self._serial,
                'nSpectra' : self.numSpectra(),
                'status' : self.status()}

    def acquire(self,milliseconds=100,dark=False,upwelling=False):
        """start recording a spectrum

        :param milliseconds: the integration time in milliseconds
        :param dark: whether a dark spectrum is recorded
        :type dark: bool
        :param upwelling: with the direction is upwelling
        :type upwelling: bool
        :return: *ok* if command successful or 'nok: message' if somethign went wrong"""

        # If the spectrometer is locked this suggests that it is already
        # acquiring a spectrum (or performing an associated task). It is not
        # possible to queue up multiple spectra, so just issue a warning
        # instead.
        if self._busy.locked():
            self.log.warning("already recording a spectrum")
            return 'nok: already recording spectrum'

        # Create an acquire task.
        task = AcquireTask()
        task.integrationTime = milliseconds
        task.dark = dark
        if upwelling is True:
            task.direction = 'upwelling'
        else:
            task.direction = 'downwelling'

        # Put the task onto the task queue. This will get picked up by
        # SpectrometerThread (if it is running).
        self._tQ.put(task)
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
        # Create a spectrometer, but don't pass a spectrometer object.
        specs.append(PiccoloSpectrometer('spectrometer{}'.format(i)))
    for s in specs:
        print s.status()
    for i in range(nSpec):
        specs[i].acquire(milliseconds=(nSpec-i)*2000)
    time.sleep(0.5)
    for s in specs:
        print s.status()

    spectra = PiccoloSpectraList()
    for s in specs:
        spec = s.getSpectrum()
        print spec.getNumberOfPixels()
        spectra.append(spec)
    spectra.write()

    time.sleep(0.5)
