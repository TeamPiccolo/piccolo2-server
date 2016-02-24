import piccolo_server as piccolo
import cherrypy

if __name__ == '__main__':

    pd = piccolo.PiccoloDispatcher(daemon=True)
    pd.registerComponent('piccolo',piccolo.Piccolo())

    pc = piccolo.PiccoloControllerCherryPy()

    pd.registerController(pc)

    pd.start()

    cherrypy.quickstart(pc)


