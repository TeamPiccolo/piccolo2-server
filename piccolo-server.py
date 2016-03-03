import piccolo_server as piccolo
import cherrypy
import argparse
import urlparse

if __name__ == '__main__':
    pcfg = piccolo.PiccoloServerConfig()

    piccolo.piccoloLogging(logfile=pcfg.cfg['logging']['logfile'],
                           debug=pcfg.cfg['logging']['debug'])

    # create data directory
    pData = piccolo.PiccoloDataDir(pcfg.cfg['datadir']['datadir'],
                                   device=pcfg.cfg['datadir']['device'],
                                   mntpnt=pcfg.cfg['datadir']['mntpnt'],
                                   mount=pcfg.cfg['datadir']['mount'])
    # initialise the piccolo component
    pc = piccolo.Piccolo('piccolo',pData)

    pd = piccolo.PiccoloDispatcher(daemon=True)
    pd.registerComponent(pc)

    pController = piccolo.PiccoloControllerCherryPy()

    pd.registerController(pController)

    pd.start()

    serverUrl = urlparse.urlparse(pcfg.cfg['jsonrpc']['url'])
    cherrypy.config.update({'server.socket_host':serverUrl.hostname,
                            'server.socket_port':serverUrl.port})

    cherrypy.quickstart(pController)


