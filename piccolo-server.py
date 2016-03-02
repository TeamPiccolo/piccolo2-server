import piccolo_server as piccolo
import cherrypy
import argparse
import urlparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true',default=False,help="enable debugging output")
    parser.add_argument('-l', '--log-file',metavar="FILE",help="send piccolo log to FILE, default stdout")
    parser.add_argument('-u','--piccolo-url',metavar='URL',default='http://localhost:8080',help='set the URL of the piccolo server, default http://localhost:8080')
    args = parser.parse_args()

    piccolo.piccoloLogging(logfile=args.log_file,debug=args.debug)

    pd = piccolo.PiccoloDispatcher(daemon=True)
    pd.registerComponent(piccolo.Piccolo('piccolo'))

    pc = piccolo.PiccoloControllerCherryPy()

    pd.registerController(pc)

    pd.start()

    serverUrl = urlparse.urlparse(args.piccolo_url)
    cherrypy.config.update({'server.socket_host':serverUrl.hostname,
                            'server.socket_port':serverUrl.port})

    cherrypy.quickstart(pc)


