import piccolo_server as piccolo
import cherrypy
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true',default=False,help="enable debugging output")
    parser.add_argument('-l', '--log-file',metavar="FILE",help="send piccolo log to FILE, default stdout")
    args = parser.parse_args()

    piccolo.piccoloLogging(logfile=args.log_file,debug=args.debug)

    pd = piccolo.PiccoloDispatcher(daemon=True)
    pd.registerComponent(piccolo.Piccolo('piccolo'))

    pc = piccolo.PiccoloControllerCherryPy()

    pd.registerController(pc)

    pd.start()

    cherrypy.quickstart(pc)


