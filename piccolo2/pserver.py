# -*- coding: utf-8 -*-
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

import server as piccolo
import cherrypy
import argparse
import urlparse
import sys
import logging
import os

import seabreeze.spectrometers as seabreeze
from piccolo2.hardware import shutters as piccolo_shutters

def piccolo_server(serverCfg):

    log = logging.getLogger("piccolo.server")

    log.info("piccolo2 server version %s"%piccolo.__version__)

    # setup the blinking status led
    piccolo.StatusLED.start()

    # create data directory
    pData = piccolo.PiccoloDataDir(serverCfg.cfg['datadir']['datadir'],
                                   device=serverCfg.cfg['datadir']['device'],
                                   mntpnt=serverCfg.cfg['datadir']['mntpnt'],
                                   mount=serverCfg.cfg['datadir']['mount'])

    # Initialize the dispatcher object (pd). The dispatcher is started later.
    #
    # Setting daemon to True ensures that it is properly terminated if Piccolo
    # Server is shut down.
    pd = piccolo.PiccoloDispatcher(daemon=True)

    # read the piccolo instrument configuration file
    piccoloCfg = piccolo.PiccoloConfig()
    cfgFilename = pData.join(serverCfg.cfg['config']) # Usually /mnt/piccolo2_data/piccolo.config
    piccoloCfg.readCfg(cfgFilename)

    # initialise the shutters
    ok=True
    for c in ['upwelling','downwelling']:
        if c not in piccoloCfg.cfg['channels']:
            log.error('{} shutter not defined'.format(c))
            ok=False
    if not ok:
        sys.exit(1)
    shutters = {}
    for c in piccoloCfg.cfg['channels']:
        if piccoloCfg.cfg['channels'][c]['shutter'] == -1:
            shutter = None
        else:
            shutter = piccolo_shutters.Shutter(getattr(piccolo_shutters,'SHUTTER_%d'%piccoloCfg.cfg['channels'][c]['shutter']))
        shutters[c] = piccolo.PiccoloShutter(c, shutter=shutter,
                                             reverse=piccoloCfg.cfg['channels'][c]['reverse'],
                                             fibreDiameter=piccoloCfg.cfg['channels'][c]['fibreDiameter'])
    for c in shutters:
        pd.registerComponent(shutters[c])

    # initialise the spectrometers
    spectrometers = {}
    for s in seabreeze.list_devices():
        #strip out all non-alphanumeric characters
        sname = 'S_'+"".join([c for c in s.serial if c.isalpha() or c.isdigit()])
        spectrometers[sname] = piccolo.PiccoloSpectrometer(sname,spectrometer=seabreeze.Spectrometer(s),calibration=piccoloCfg.getCalibration(sname[2:]))
    if len(spectrometers) == 0:
        for sn in piccoloCfg.cfg['spectrometers']:
            sname = 'S_'+sn
            s = None
            spectrometers[sname] = piccolo.PiccoloSpectrometer(sname,spectrometer=s,calibration=piccoloCfg.getCalibration(sname[2:]))
    # Set the spectrometer temperatures (for spectrometers that have a settable detector temperature).
    hasTEC = dict() # The spectrometer has a TEC and its temperature can be adjusted.
    temperaturesToSet = dict()
    for sname in spectrometers:
        spectrometer_serial_number = spectrometers[sname]._spectrometer._spec.serial_number
        #FIXME hasTEC[spectrometer_serial_number] = spectrometers[sname]._spectrometer._spec.detectorTemperatureCanBeSet
    for spectrometer_serial_number in piccoloCfg.cfg['spectrometers']:
        spectrometer_custom_configuration = piccoloCfg.cfg['spectrometers'][spectrometer_serial_number]
        if 'temperatureDetectorSet' in spectrometer_custom_configuration:
            temperature = spectrometer_custom_configuration['temperatureDetectorSet'] # This appears to read a string, not a float.
            temperaturesToSet[spectrometer_serial_number] = temperature
    # Log warnings if necessary.
    log.info('{}'.format(hasTEC)) # ...need to format meaningfully.
    log.info('{}'.format(temperaturesToSet)) # ...need to format meaningfully.

    for s in temperaturesToSet:
        if s in hasTEC:
            for sname in spectrometers:
                if spectrometers[sname]._spectrometer._spec.serial_number == s:
                    log.info('Setting the detector temperature of {} to {} °C...'.format(sname, temperaturesToSet[s]))
                    spectrometers[sname]._spectrometer._spec.set_tec_setpoint(float(temperaturesToSet[s]))
            #set_tec_setpoint(temperaturesToSet)
    # Convert the sname to the serial number.
    #spectrometer_manufacturer = spectrometers[sname]._spectrometer._spec.manufacturer
    #spectrometer_model = spectrometers[sname]._spectrometer._spec.model
    # Does the spectrometer have a thermoelectric cooler (TEC)?

#    if hasTEC:
#        log.info('The {} {} {} has a thermoelectric cooler.'.format(spectrometer_manufacturer, spectrometer_model, spectrometer_serial_number))
#    else:
#        log.info('The {} {} {} does not have any thermoelectric cooler.'.format(spectrometer_manufacturer, spectrometer_model, spectrometer_serial_number))
    for sname in spectrometers:
        if sname[2:] in piccoloCfg.cfg['spectrometers']:
            spectrometers[sname].minIntegrationTime = piccoloCfg.cfg['spectrometers'][sname[2:]]['min_integration_time']
            spectrometers[sname].maxIntegrationTime = piccoloCfg.cfg['spectrometers'][sname[2:]]['max_integration_time']
        pd.registerComponent(spectrometers[sname])

    # Look for calibration data related to each of the connected spectrometers.
    for sname in spectrometers:
        serial = sname[2:]
        if 'calibrations' in piccoloCfg.cfg and serial in piccoloCfg.cfg['calibrations']:
            log.info('Reading calibration of spectrometer {} from instrument configuration file.'.format(serial))
            for channel in piccoloCfg.cfg['channels']:
                if channel in piccoloCfg.cfg['calibrations'][serial]:
                    wavcal = piccoloCfg.cfg['calibrations'][serial][channel]['wavelengthCalibrationCoefficientsPiccolo']
                    log.info('Spectrometer {} wavelength calibration coefficients for channel {} read from instrument configuration file: {}'.format(serial, channel, wavcal))
                else:
                    log.error('Spectrometer {} is missing wavelength calibration data for channel {} in the instrument configuration file.'.format(serial, channel))
        else:
            log.warning('No calibration section for the spectrometer {}'.format(serial))

    # initialize the gps
    gps = piccolo.PiccoloGPS()
    # initialise the piccolo component
    pc = piccolo.Piccolo('piccolo',pData,shutters,spectrometers,gps,
                         clobber=piccoloCfg.cfg['output']['clobber'],
                         split=piccoloCfg.cfg['output']['split'],
                         cfg = piccoloCfg.cfg )
    pd.registerComponent(pc)

    pJSONController = piccolo.PiccoloControllerCherryPy()
    pd.registerController(pJSONController)

    pXBEEController = None
    try:
        pXBEEController = piccolo.PiccoloControllerXbee()
        piccolo.StatusLED.show_spectrometers(spectrometers)
    except Exception as e:
        log.warn('Cannot initialise the XBee radio controller because an exception occurred. {}'.format(e))
        piccolo.StatusLED.not_ok()

    if pXBEEController!=None:
        pd.registerController(pXBEEController)

    pd.start()

    # start the webservice
    serverUrl = urlparse.urlparse(serverCfg.cfg['jsonrpc']['url'])
    cherrypy.config.update({'server.socket_host':serverUrl.hostname,
                                'server.socket_port':serverUrl.port})
    # redirect log if daemonized
    if serverCfg.cfg['daemon']['daemon']:
        cherrypy.config.update({'log.screen': False,
                                'log.access_file': serverCfg.cfg['jsonrpc']['access_log'],
                                'log.error_file':  serverCfg.cfg['jsonrpc']['error_log']})

    cherrypy.quickstart(pJSONController)

def main():
    serverCfg = piccolo.PiccoloServerConfig()

    # start logging
    handler = piccolo.piccoloLogging(logfile=serverCfg.cfg['logging']['logfile'],
                                     debug=serverCfg.cfg['logging']['debug'])
    log = logging.getLogger("piccolo.server")

    if serverCfg.cfg['daemon']['daemon']:
        import daemon
        try:
            import lockfile
        except ImportError:
            print "The 'lockfile' Python module is required to run Piccolo Server. Ensure that version 0.12 or later of lockfile is installed."
            sys.exit(1)
        try:
            from lockfile.pidlockfile import PIDLockFile
        except ImportError:
            print "An outdated version of the 'lockfile' Python module is installed. Piccolo Server requires at least version 0.12 or later of lockfile."
            sys.exit(1)
        from lockfile import AlreadyLocked, NotLocked

        # create a pid file and tidy up if required
        pidfile = PIDLockFile(serverCfg.cfg['daemon']['pid_file'], timeout=-1)
        try:
            pidfile.acquire()
        except AlreadyLocked:
            try:
                os.kill(pidfile.read_pid(), 0)
                print 'Process already running!'
                exit(1)
            except OSError:  #No process with locked PID
                print 'PID file exists but process is dead'
                pidfile.break_lock()
        try:
            pidfile.release()
        except NotLocked:
            pass

        pstd = open('/var/log/piccolo.err','w')
        with daemon.DaemonContext(pidfile=pidfile,
                                  files_preserve = [ handler.stream ],
                                  stderr=pstd):
            # start piccolo
            piccolo_server(serverCfg)
    else:
        # start piccolo
        piccolo_server(serverCfg)

    piccolo.StatusLED.stop()

if __name__ == '__main__':
    main()
