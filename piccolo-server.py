import piccolo_server as piccolo
import cherrypy
import argparse
import urlparse
import sys
import logging

if __name__ == '__main__':
    serverCfg = piccolo.PiccoloServerConfig()

    piccolo.piccoloLogging(logfile=serverCfg.cfg['logging']['logfile'],
                           debug=serverCfg.cfg['logging']['debug'])

    log = logging.getLogger("piccolo.server")

    # create data directory
    pData = piccolo.PiccoloDataDir(serverCfg.cfg['datadir']['datadir'],
                                   device=serverCfg.cfg['datadir']['device'],
                                   mntpnt=serverCfg.cfg['datadir']['mntpnt'],
                                   mount=serverCfg.cfg['datadir']['mount'])

    # start the dispatcher
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
            raise NotImplementedError('Shutter supported not implemented. Set the shutter numbers to be -1 in the Piccolo server configuration file.')
        shutters[c] = piccolo.PiccoloShutter(c, shutter=shutter,
                                             reverse=piccoloCfg.cfg['channels'][c]['reverse'],
                                             fibreDiameter=piccoloCfg.cfg['channels'][c]['fibreDiameter'])
    for c in shutters:
        pd.registerComponent(shutters[c])

    # initialise the spectrometers
    spectrometers = {}
    for sname in piccoloCfg.cfg['spectrometers']:
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
