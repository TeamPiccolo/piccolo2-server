import server as piccolo
import cherrypy
import argparse
import urlparse
import sys
import logging

HAVE_PICCOLO_DRIVER = True
try:
    import piccolo2.hardware
except:
    HAVE_PICCOLO_DRIVER = False

if HAVE_PICCOLO_DRIVER:
    from piccolo2.hardware import shutters as piccolo_shutters
    from piccolo2.hardware import spectrometers as piccolo_spectrometers

def main():
    serverCfg = piccolo.PiccoloServerConfig()

    piccolo.piccoloLogging(logfile=serverCfg.cfg['logging']['logfile'],
                           debug=serverCfg.cfg['logging']['debug'])

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
    else:
        for sn in piccoloCfg.cfg['spectrometers']:
            sname = 'S_'+sn
            spectrometers[sname] = piccolo.PiccoloSpectrometer(sname)
    for sname in spectrometers:
        pd.registerComponent(spectrometers[sname])

    # initialise the piccolo component
    pc = piccolo.Piccolo('piccolo',pData,shutters,spectrometers)
    pd.registerComponent(pc)



    pController = piccolo.PiccoloControllerCherryPy()

    pd.registerController(pController)

    pd.start()

    # start the webservice
    serverUrl = urlparse.urlparse(serverCfg.cfg['jsonrpc']['url'])
    cherrypy.config.update({'server.socket_host':serverUrl.hostname,
                            'server.socket_port':serverUrl.port})

    cherrypy.quickstart(pController)

if __name__ == '__main__':
    main()
