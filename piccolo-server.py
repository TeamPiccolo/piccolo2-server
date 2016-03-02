import piccolo_server as piccolo
import cherrypy
import argparse
import urlparse

if __name__ == '__main__':
    pcfg = piccolo.PiccoloServerConfig()

    piccolo.piccoloLogging(logfile=pcfg.cfg['logging']['logfile'],
                           debug=pcfg.cfg['logging']['debug'])

    pd = piccolo.PiccoloDispatcher(daemon=True)
    pd.registerComponent(piccolo.Piccolo('piccolo'))

    pc = piccolo.PiccoloControllerCherryPy()

    pd.registerController(pc)

    pd.start()

    serverUrl = urlparse.urlparse(pcfg.cfg['jsonrpc']['url'])
    cherrypy.config.update({'server.socket_host':serverUrl.hostname,
                            'server.socket_port':serverUrl.port})

    cherrypy.quickstart(pc)


