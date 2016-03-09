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

    # initialise the piccolo component
    pc = piccolo.Piccolo('piccolo',pData)
    pd.registerComponent(pc)

    # initialise the shutters
    ok=True
    for c in ['upwelling','downwelling']:
        if c not in piccoloCfg.cfg['channels']:
            log.error('{} shutter not defined'.format(c))
            ok=False
    if not ok:
        sys.exit(1)
    cname = 'upwelling'
    upwellingShutter = piccolo.PiccoloShutter(
        cname,
        channel=piccoloCfg.cfg['channels'][cname]['shutter'],
        reverse=piccoloCfg.cfg['channels'][cname]['reverse'],
        fibreDiameter=piccoloCfg.cfg['channels'][cname]['fibreDiameter'])
    pd.registerComponent(upwellingShutter)
    cname = 'downwelling'
    downwellingShutter = piccolo.PiccoloShutter(
        cname,
        channel=piccoloCfg.cfg['channels'][cname]['shutter'],
        reverse=piccoloCfg.cfg['channels'][cname]['reverse'],
        fibreDiameter=piccoloCfg.cfg['channels'][cname]['fibreDiameter'])
    pd.registerComponent(downwellingShutter)
    
    # initialise the spectrometers
    spectrometers = []
    for sname in piccoloCfg.cfg['spectrometers']:
        spectrometers.append(piccolo.PiccoloSpectrometer(sname))
    for s in spectrometers:
        pd.registerComponent(s)

    pController = piccolo.PiccoloControllerCherryPy()

    pd.registerController(pController)

    pd.start()

    serverUrl = urlparse.urlparse(serverCfg.cfg['jsonrpc']['url'])
    cherrypy.config.update({'server.socket_host':serverUrl.hostname,
                            'server.socket_port':serverUrl.port})

    cherrypy.quickstart(pController)


