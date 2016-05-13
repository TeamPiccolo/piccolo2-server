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

HAVE_PICCOLO_DRIVER = True
try:
    import piccolo2.hardware
except:
    HAVE_PICCOLO_DRIVER = False

if HAVE_PICCOLO_DRIVER:
    from piccolo2.hardware import shutters as piccolo_shutters
    from piccolo2.hardware import spectrometers as piccolo_spectrometers
    
def piccolo_server(serverCfg):

    log = logging.getLogger("piccolo.server")

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

    # read the piccolo configuration
    piccoloCfg = piccolo.PiccoloConfig()
    piccoloCfg.readCfg(pData.join(serverCfg.cfg['config']))

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
            if not HAVE_PICCOLO_DRIVER:
                log.error('piccolo low-level drivers are not available')
                sys.exit(1)
            shutter = piccolo_shutters.Shutter(getattr(piccolo_shutters,'SHUTTER_%d'%piccoloCfg.cfg['channels'][c]['shutter']))
        shutters[c] = piccolo.PiccoloShutter(c, shutter=shutter,
                                             reverse=piccoloCfg.cfg['channels'][c]['reverse'],
                                             fibreDiameter=piccoloCfg.cfg['channels'][c]['fibreDiameter'])
    for c in shutters:
        pd.registerComponent(shutters[c])

    # initialise the spectrometers
    spectrometers = {}
    if HAVE_PICCOLO_DRIVER:
        for s in piccolo_spectrometers.getConnectedSpectrometers():
            
            #strip out all non-alphanumeric characters
            sname = 'S_'+"".join([c for c in s.serialNumber if c.isalpha() or c.isdigit()])
            spectrometers[sname] = piccolo.PiccoloSpectrometer(sname,spectrometer=s)
    if len(spectrometers) == 0:
        for sn in piccoloCfg.cfg['spectrometers']:
            sname = 'S_'+sn
            if HAVE_PICCOLO_DRIVER:
                s = piccolo_spectrometers.SimulatedOceanOpticsSpectrometer(sn)
            else:
                s = None
            spectrometers[sname] = piccolo.PiccoloSpectrometer(sname,spectrometer=s)
    for sname in spectrometers:
        pd.registerComponent(spectrometers[sname])

    # initialise the piccolo component
    pc = piccolo.Piccolo('piccolo',pData,shutters,spectrometers)
    pd.registerComponent(pc)

    pJSONController = piccolo.PiccoloControllerCherryPy()
    pd.registerController(pJSONController)

    pXBEEController = None
    try:
        pXBEEController = piccolo.PiccoloControllerXbee()
    except:
        log.warn('cannot initialise xbee controller')
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
        from lockfile.pidlockfile import PIDLockFile
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
    
if __name__ == '__main__':
    main()
