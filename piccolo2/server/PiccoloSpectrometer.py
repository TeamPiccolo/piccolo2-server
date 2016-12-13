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
.. moduleauthor:: Iain Robinson <iain.robinson@ed.ac.uk>
"""

__all__ = ['PiccoloSpectrometer']

from piccolo2.PiccoloSpectra import *
from PiccoloInstrument import PiccoloInstrument
from PiccoloWorkerThread import PiccoloWorkerThread
import time
import threading
from Queue import Queue
import logging

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
            spectrum['name'] = self.name

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
    """Class to communicate with a spectrometer."""

    def __init__(self,name,spectrometer=None):

        PiccoloInstrument.__init__(self,name)

        # The lock prevents two threads using the spectrometer at the same time.
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
