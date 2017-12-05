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
#
# You should have received a copy of the GNU General Public License
# along with piccolo2-server.  If not, see <http://www.gnu.org/licenses/>.

"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>
.. moduleauthor:: Iain Robinson <iain@physics.org>

The Piccolo Spectrometer module handles communication with the spectrometers. It
uses threading to enable spectrometers to acquire in the background whilst other
tasks (such as communication) are being performed.
"""

__all__ = ['PiccoloSpectrometer']

from piccolo2.PiccoloSpectra import *
from PiccoloInstrument import PiccoloInstrument
from PiccoloWorkerThread import PiccoloWorkerThread
import time
import threading
from Queue import Queue
import logging
try:
    from piccolo2.hardware.spectrometers import AutointegrationNoLightError
    from piccolo2.hardware.spectrometers import AutointegrationUnstableLightError
    from piccolo2.hardware.spectrometers import AutointegrationExceededMaximumIntegrationTimeError
except ImportError:
    logging.warn("Using outdated spectrometer drivers.")
    AutointegrationNoLightError = Exception
    AutointegrationUnstableLightError = Exception
    AutointegrationExceededMaximumIntegrationTimeError = Exception
import sys

class Task(object):
    """Instructions for a specific action which the spectrometer is to perform.

    Currently the spectrometer can perform two types of task: autointegrate
    and acquire. These task types are subclasses of Task.

    Every Task produces a corresponding Result, defined in the Result class.
    """
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

    def __str__(self):
        if self.dark:
            type_str = "dark"
        else:
            type_str = "light"
        return "{} {} spectrum at {} ms integration time".format(self.direction, type_str, self.integrationTime)

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

    def __init__(self):
        self._tmin = None # Minimum permitted integration time in milliseconds.
        self._tmax = None # Maximum permitted integration time in milliseconds.
        self._target = 0.7 # Best peak counts as a percentage of saturation.

    @property
    def target(self):
        """Returns the target peak level in the spectrum as a fraction of the
        saturation level.

        :returns:   float -- target as a fraction
        """
        if self._target is None:
            raise Exception('The target for the autointegration algorithm has not been set.')
        return self._target

    @property
    def targetPercent(self):
        """Returns the target peak level in the spectrum as a percentage.

        :returns:    float -- target as a percentage
        """
        return 100 * self._target

    @target.setter
    def target(self, p):
        """Set the target peak level in the spectrum as a fraction of the saturation level.

        The autointegration algorithm determines the integration time that will
        give a peak value in the spectrum that is close to the spectrometer's
        saturation level. Exactly how close can be customized by setting the
        target to some fraction of the saturation level. For example, setting
        the target to 70 % (the default) should provide an integration time
        that results in a spectrum with a peak value that is 70 % of the saturation
        level.

        :param p: target peak level as a fraction of saturation level
        :type p: float
        """
        try:
            p_float = float(p)
        except ValueError:
            raise Exception('The autointegration target peak value must be a number. {} is type {}.'.format(p, type(p)))
        if p_float < 0.01:
            raise Exception('The autointegration target peak value, {} %, is below 1 % of the saturation level and this seems too low.'.format(100*p_float))
        if p_float > 1.0:
            raise Exception('The autointegratiopn target peak value, {} %, is greater than 100 %. Targets exceeding 100 % of saturation are not allowed.'.format(100*p_float))
        self._target = p_float

    @targetPercent.setter
    def targetPercent(self, p):
        """Set the target peak level in the spectrum as a percentage.

        :param p: target peak level as a percentage
        :type p: int or float
        """
        try:
            p_float = float(p)
        except ValueError:
            raise Exception('The autointegration peak value must be a percentage. {} is type {}.'.format(p, type(p)))
        self.target = p_float / float(100)

    @property
    def minimumIntegrationTime(self):
        """Get the minimum integration time that autointegration can return.

        :returns:  float -- integration time in milliseconds.
        """
        return self._tmin
        
    @minimumIntegrationTime.setter
    def minimumIntegrationTime(self, t):
        """Set the minimum integration time that autointegration will go to.

        Autointegration determines the best integration time for the spectrum.
        This function sets the minimum integration time that it may return. It
        can be used to avoid having autointegration set very long integration
        times on the spectrometer.

        The default value is None. If set to None, it will default to the
        minimum integration time supported by the spectrometer. This will vary
        from model to model, but is typically about 1 min.

        :param t: minimum integration time in milliseconds.
        :type t: float or int
        """
        try:
            tFloat = float(t) # t could be an integer or a float.
        except ValueError as e:
            raise ValueError('The integration time must be a number. {} is {}.'.format(t, type(t)))
        if tFloat < 0:
            raise ValueError("The integration time cannot be negative.")
        self._tmin = tFloat

    @property
    def maximumIntegrationTime(self):
        """Get the maximum integration time that autointegration can return.

        :returns:  float -- integration time in milliseconds.
        """
        return self._tmax

    @maximumIntegrationTime.setter
    def maximumIntegrationTime(self, t):
        """Set the maximum integration time that autointegration will go to.

        Autointegration determines the best integration time for the spectrum.
        This function sets the maximum integration time that it may return. It
        can be used to avoid having autointegration set very long integration
        times on the spectrometer.

        The default value is None. If set to None, it will default to the
        maximum integration time supported by the spectrometer. This will vary
        from model to model, but is typically about 1 min.

        :param t: maximum integration time in milliseconds.
        :type t: float or int
        """
        try:
            tFloat = float(t) # t could be an integer or a float.
        except ValueError as e:
            raise ValueError('The integration time must be a number. {} is {}.'.format(t, type(t)))
        if tFloat < 0:
            raise ValueError("The integration time cannot be negative.")
        self._tmax = tFloat

    def __str__(self):
        t_max = self.maximumIntegrationTime
        if t_max is None:
            max_string = ""
        else:
            max_string = " and {} ms maximum integration time".format(t_max)
        return "target {}% of saturation".format(self.targetPercent) + max_string

class MinMaxIntegrationTimeTask(Task):
    def __init__(self,minTime=None,maxTime=None):
        self.minIntegrationTime = minTime
        self.maxIntegrationTime = maxTime
    
class Result(object):
    pass

class AutointegrateResult(Result):
    """Class to hold the result of an autointegration."""
    def __init__(self):
        self._error = "" # Empty string means no error.
        self._t = None # The best integration time or None if autointegration failed.
        self._debug = None # Optional debug data.

    @property
    def success(self):
        if self._t is None:
            return False
        else:
            return True
    @success.setter
    def success(self, S):
        raise Exception('Success is a read-only property.')

    @property
    def errorMessage(self):
        if self.success:
            raise Exception('There is no error message from autointegration because the autointegration algorithm worked and return time {} ms'.format(self.bestIntegrationTime))
        if len(self._error) == 0:
            raise Exception('The autointegration algorithm failed, but did not provide an error message.')
        return self._error
    @errorMessage.setter
    def errorMessage(self, message):
        if len(self._error) > 0:
            raise Exception('Cannot overwrite autointegraiton error message.')
        self._error = message

    @property
    def bestIntegrationTime(self):
        """Returns the best integration time in milliseconds."""
        if not self.success:
            raise Exception('Could not get the best integration time because the autointegration algorithm failed.')
        return self._t
    @bestIntegrationTime.setter
    def bestIntegrationTime(self, t):
        if t < 0:
            raise Exception('The best integratipon time ({}) cannot be negative.'.format(t))
        self._t = t

    def __str__(self):
        if self.success:
            return "{} ms is the best integration time.".format(self.bestIntegrationTime)
        else:
            return "Autointegration failed: {}".format(self.errorMessage)

class SpectrometerThread(PiccoloWorkerThread):
    """Spectrometer worker thread object. The worker thread performs assigned
       tasks in the background and holds on to the results until they are
       picked up."""

    LOGNAME = 'spectrometer'

    def __init__(self, name, spectrometer, busy, tasks, results,integration_times):
        """Initialize the worker thread.

        Note: calling __init__ does not start the thread, a subsequent call to
        start() is needed to start the thread.

        :param name: ?
        :type name: str
        :param spectrometer: A PiccoloSpectrometer object
        :type spectrometer: PiccoloSpectrometer
        :param busy: a "lock" which prevents using the spectrometer when it is busy
        :type busy: thread.lock
        :param tasks: a queue into which tasks will be put
        :type tasks: Queue.Queue
        :param results: the results queue from where results will be collected
        :type results: Queue.Queue
        :param integration_times: queue for reporting integration times
        :type results: Queue.Queue
        """
        PiccoloWorkerThread.__init__(self, name, busy, tasks, results)
        self._spec = spectrometer
        self._itQ = integration_times
  
    def run(self):
        while True:
            # wait for a new task from the task queue
            task = self.tasks.get()
            if task == None:
                # The worker thread can be stopped by putting a None onto the task queue.
                self.log.info('Stopped worker thread for specrometer {}.'.format(self.name))
                return
            self._performTask(task)

    def _performTask(self, task):
        if not isinstance(task, Task):
            raise TypeError('Unrecognized task type {}'.format(type(task)))

        # The spectrometer can only perform one task at a time. What should
        # happen if it is already performing a task? For now, if the
        # spectrometer is locked, just raise an Exception.
        if self.busy.locked():
            raise Exception('Cannot perform task {} because the spectrometer is locked.')
        self.busy.acquire() # This command locks the spectrometer. ("acquire" here refers to the lock, not the spectrometer!)

        # Check what the type of the task is, then perform it.
        if type(task) is AcquireTask:
            self._performAcquireTask(task)
        elif type(task) is AutointegrateTask:
            self._performAutointegrateTask(task)
        elif type(task) is MinMaxIntegrationTimeTask:
            self._performIntegrationTimeTask(task)

        # The task has completed, so unlock the spectrometer. The result of the
        # task should now be on the results queue waiting to be picked up.
        self.busy.release()

    def _performAutointegrateTask(self, task):
        self.log.debug('Performing an autointegrate task: {}'.format(task))
        # Create the result object.
        result = AutointegrateResult()
        # Need to add support for a maximum integration time (at which
        # the algorithm will fail).
        t = None
        try:
            t = self._spec.findBestIntegrationTime(percent=task.targetPercent)
            result.bestIntegrationTime = t
        except AutointegrationNoLightError as e:
            # The exception will contain a message with information about why
            # autointegration failed. Copy this message into the result object.
            result.errorMessage = e.message
        except AutointegrationUnstableLightError as e:
            result.errorMessage = e.message
        except AutointegrationExceededMaximumIntegrationTimeError as e:
            result.errorMessage = e.message
        except Exception as e:
            # Get information about the exception.
            self.log.exception('An unanticipated error occured during autointegration on spectroemter {}.'.format(self._spec.serialNumber))
            raise
        self.results.put(result)

    def _performAcquireTask(self, task):
        self.log.debug("Performing an acquire task: {}".format(task))
        self.log.info("Acquiring a spectrum with {} millisecond integration time.".format(task.integrationTime))

        # create new spectrum instance
        spectrum = PiccoloSpectrum()
        if task.dark:
            spectrum.setDark()
        else:
            spectrum.setLight()
        if task.direction == 'upwelling':
            spectrum.setUpwelling(True)
        elif task.direction == 'downwelling':
            spectrum.setUpwelling(False)
        else:
            raise Exception('Unsupported direction: "{}"'.format(task.direction))
        spectrum['name'] = self.name

        # record data
        if self._spec==None:
            # If spectrometer is None, thenm simulate a spectrometer, for
            # testing purposes.
            time.sleep(task.integrationTime/1000.)
            pixels = [1]*100
        else:
            # Have a real spectrometer, so acquire a real spectrum.
            self._spec.setIntegrationTime(task.integrationTime)
            spectrum.update(self._spec.getMetadata())
            self._spec.requestSpectrum()
            pixels = self._spec.readSpectrum()

        spectrum.pixels = pixels

        # write results to the result queue
        self.results.put(spectrum)

    def _performIntegrationTimeTask(self,task):
        self.log.debug("setting/getting integration times")
        for t in ['minIntegrationTime','maxIntegrationTime']:
            if getattr(task,t) is not None:
                setattr(self._spec,t,getattr(task,t))
        results = {}
        for t in ['minIntegrationTime','maxIntegrationTime','currentIntegrationTime']:
            results[t] = getattr(self._spec,t)
        results['currentIntegrationTime'] = results['currentIntegrationTime'].getMilliseconds()
        self._itQ.put(results)
            
            
class PiccoloSpectrometer(PiccoloInstrument):
    """Class to communicate with a spectrometer."""

    def __init__(self, name, spectrometer=None):
        """Initialize a Piccolo Spectrometer object for Piccolo Server.

           The spectromter parameter must be the Spectrometer object from the
           Piccolo Hardware module, such as OceanOpticsUSB2000Plus or
           OceanOpticsQEPro.

           name is a descriptive name for the spectrometer.

           :param name: a descriptive name for the spectrometer.
           :param spectrometer: the spectromtere, which may be None.
        """

        PiccoloInstrument.__init__(self, name)

        # The lock prevents two threads using the spectrometer at the same time.
        self._busy = threading.Lock()
        self._tQ = Queue() # Task queue.
        self._rQ = Queue() # Results queue.
        self._itQ = Queue() # for getting the current integration times

        if spectrometer is None:
            self.log.warning('A PiccoloSpectrometer object has been created without a Spectrometer hadware object. This is usually only done for testing the Piccolo code. You should not see this message during normal operation.')
            self._serial = None
        else:
            self._serial = spectrometer.serialNumber


        self._spectrometer = SpectrometerThread(name, spectrometer, self._busy, self._tQ, self._rQ, self._itQ)
        self._spectrometer.start() # Start the thread.
        self.updateIntegrationTimes() # get integration times

    def __del__(self):
        # send poison pill to worker
        self._tQ.put(None)

    def updateIntegrationTimes(self,minIntegrationTime=None,maxIntegrationTime=None):
        if self._busy.locked():
            self.log.warning("busy, cannot manipulate integration times")
            return 'nok: busy'
        task = MinMaxIntegrationTimeTask(minTime=minIntegrationTime,maxTime=maxIntegrationTime)
        self._tQ.put(task)
        times = self._itQ.get()
        self._currentIntegrationTime = times['currentIntegrationTime']
        self._minIntegrationTime = times['minIntegrationTime']
        self._maxIntegrationTime = times['maxIntegrationTime']
        
    def getCurrentIntegrationTime(self):
        return self._currentIntegrationTime
    def getMinIntegrationTime(self):
        return self._minIntegrationTime
    def setMinIntegrationTime(self,milliseconds):
        self.updateIntegrationTimes(minIntegrationTime=milliseconds)
    def getMaxIntegrationTime(self):
        return self._maxIntegrationTime
    def setMaxIntegrationTime(self,milliseconds):
        self.updateIntegrationTimes(maxIntegrationTime=milliseconds)
        
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
                'status' : self.status(),
                'currentIntegrationTime' : self.getCurrentIntegrationTime(),
                'minIntegrationTime' : self.getMinIntegrationTime(),
                'maxIntegrationTime' : self.getMaxIntegrationTime(),
                }

    def acquire(self, milliseconds=100, dark=False, shutter='upwelling'):
        """Start acquiring ("recording") a spectrum.

        :param milliseconds: the integration time in milliseconds
        :param dark: whether a dark spectrum is recorded
        :type dark: bool
        :param upwelling: the name of the shutter
        :type shutter: string
        :return: "ok" if command successful or "nok: message" if something went wrong
        """

        # If the spectrometer is locked this suggests that it is already
        # acquiring a spectrum (or performing an associated task). It is not
        # possible to queue up acquisition tasks, so just issue a warning
        # instead.
        if self._busy.locked():
            self.log.warning("already recording a spectrum")
            return 'nok: already recording spectrum'

        # Create an acquire task and set its parameters.
        task = AcquireTask()
        task.integrationTime = milliseconds
        task.dark = dark
        task.direction = shutter

        # Put the task onto the task queue. This will get picked up by
        # SpectrometerThread (if it is running).
        self._tQ.put(task)
        return 'ok'

    def getSpectrum(self):
        """Get a spectrum.

        Spectra are acquired using the acquire function. Once acquired, spectra
        are held on a queue until they are picked up with this function.

        If the spectrometer is busy (acquiring a spectrum) then this function
        will wait, possibly forever, until a spectrum is available.

        If the spectrometer is idle (not acquiring a spectrum) then this
        function will wait, up to a maximum of 5 seconds, for a spectrum
        to become available. If there is still no spectrum is available, an
        exception (type Queue.Empty) is raised. This error occurs when an
        attempt is made to get a spectrum without first acquiring one.

        raises: An expcetion if there is not spectrum ready (after waiting).
        retruns:
        rtype:
        """

        block=True
        if self._busy.locked():
            # The spectrometer is busy acquiring a specturm. If no spectrum is
            # available now, wait until it is finished, however long it takes.
            self.log.debug("busy, waiting until spectrum is available")
            timeout = None
        else:
            # The spectrometer is idle. This situation can occur if:
            # 1. getSpectrum() was called without first calling acquire().
            # 2. acquire() was called, but the worker thread has not yet started
            #    the acquisition..
            # 3. acquire() was called, but the worker thread is not running.
            # Situations 1 and 3 are errors. Situation 2 is normal. To prevent
            # unnecessary errors, a short delay (5 seconds) is required here.
            self.log.debug("idle, waiting at most 5s for spectrum")
            timeout = 5
        result = self._rQ.get(block, timeout)
        if isinstance(result, PiccoloSpectrum):
            return result
        else:
            # An error could occur if an aucointegration is requested, but then
            # a spectrum is read (instead of an autointegration result).
            raise Exception('Tried to get a spectrum, but found a {}: {}'.format(type(result), result))

    def autointegrate(self):
        """Determines the best integration time."""
        if self._busy.locked():
            self.log.warning("Spectrometer busy. Cannot autointegrate.".format())
            return 'nok: already acquiring or autointegrating'

        # Create an autointegrate task.
        task = AutointegrateTask()
        task.minimumIntegrationTime = self.getMinIntegrationTime()
        task.maximumIntegrationTime = self.getMaxIntegrationTime()

        # Put the autointegrate task onto the task queue.
        self._tQ.put(task)
        return 'ok'

    def getAutointegrateResult(self):
        """Returns the best integration time."""
        block=True
        if self._busy.locked():
            self.log.debug("busy, waiting until the autointegration procedure has completed")
            timeout = None
        else:
            self.log.debug("idle, waiting at most 20s")
            timeout = 20
        result = self._rQ.get(block, timeout)
        if isinstance(result, AutointegrateResult):
            return result

if __name__ == '__main__':
    # This code is used to test the PiccoloSpectrometer module in Piccolo Server
    # It is not used during normal operation.
    from piccoloLogging import *
    #from matplotlib import pyplot as plt

    have_hardware = False # True if the hardware drivers are available
    try:
        from piccolo2.hardware import spectrometers as piccolo_spectrometers
        have_hardware = True
    except ImportError as e:
        print "Hardware drivers are not available."

    piccoloLogging(debug=True)

    # Detect and initialize the spectrometers, or simulate some spectrometers if
    # none are connected.
    spectrometers = []
    if have_hardware:
        for s in piccolo_spectrometers.getConnectedSpectrometers():
            #strip out all non-alphanumeric characters
            sname = 'S_'+"".join([c for c in s.serialNumber if c.isalpha() or c.isdigit()])
            spectrometers.append(PiccoloSpectrometer(sname,spectrometer=s))
    if len(spectrometers) == 0: # No hardware drivers, or no spectrometers detected.
        nSpectrometers = 2
        print "No spectrometers connected. {} spectrometers will be simulated.".format(nSpectrometers)
        for i in range(nSpectrometers):
            sname = 'spectrometer{}'.format(i)
            if have_hardware:
                s = piccolo_spectrometers.SimulatedOceanOpticsSpectrometer(sname)
            else:
                s = none
            # Create a spectrometer, but don't pass a spectrometer object.
            spectrometers.append(PiccoloSpectrometer(sname,spectrometer=s))

    for s in spectrometers:
        info = s.info()
        print 'Spectrometer {} is {}'.format(info['serial'], info['status'])
        print info
        
    best = {}
    print 'Determining best integration times...'
    # This will fail if tested with "simulated" spectroemters.
    for s in spectrometers:
        serial = s.info()['serial']
        s.autointegrate()
        r = s.getAutointegrateResult()
        if not r.success:
            # Autointegration failed.
            print "Autointegration on spectrometer {} failed: {}".format(serial, r.errorMessage)
            sys.exit(1)
        t = r.bestIntegrationTime
        print 'Spectrometer {} integration time {} ms'.format(serial, t)
        best[serial] = t

    print 'Starting acquisitions...'
    for i in range(len(spectrometers)):
        serial = spectrometers[i].info()['serial']
        t = best[serial]
        spectrometers[i].acquire(milliseconds=t)

    for s in spectrometers:
        info = s.info()
        print 'Spectrometer {} is {}'.format(info['serial'], info['status'])

    print 'Waiting for half a second...'
    time.sleep(0.5)
    for s in spectrometers:
        info = s.info()
        print 'Spectrometer {} is {}'.format(info['serial'], info['status'])

    spectra = PiccoloSpectraList()
    for s in spectrometers:
        spec = s.getSpectrum()
        print "Got a spectrum with {} pixels".format(spec.getNumberOfPixels())
        plt.plot(spec.pixels)
        plt.show()
        spectra.append(spec)
#    spectra.write()


    time.sleep(0.5)
