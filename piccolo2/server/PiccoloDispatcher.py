"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloDispatcher']

import threading
import time
import sys
from PiccoloInstrument import PiccoloInstrument
from PiccoloController import PiccoloController

class PiccoloDispatcher(threading.Thread):
    """piccolo dispatcher class
    
    The dispatcher sits at the centre and takes instructions from the
    controllers and passes them on to the instruments. 
    """

    DELAY = 0.1
    
    def __init__(self,daemon=False):
        """
        :param daemon: whether the dispatcher thread should be daemonised. When
                       set to true, the dispatcher thread stops when the main
                       thread stops. default False
        :type daemon: logical"""
        threading.Thread.__init__(self,name="PiccoloDispatcher")

        self.daemon = daemon
        self._components = {}
        self._clients = []

    def registerComponent(self,component):
        """register a component, ie instrument

        :param component: the instance of a piccolo instrument
        :type component: PiccoloInstrument"""
        assert isinstance(component,PiccoloInstrument)
        self._components[component.name] = component

    def registerController(self,controller):
        """register a controller
        
        :param controller: instance of a controller
        :type controller: PiccoloController"""
        #assert isinstance(controller,PiccoloController)
        self._clients.append((controller.taskQ,controller.doneQ))
        
    def getComponentList(self):
        """get list of registered components
        :returns: list of components"""
        return self._components.keys()

    def invoke(self,component,command,kwds={}):
        """run command on a component

        :param component: the name of the component to run command on
        :param command: the command to run
        :param kwds: dictionary containing command parameters
        :returns: result of running command"""
        if component not in self._components:
            raise KeyError, 'unkown component {0}'.format(component)
        if not hasattr(self._components[component],command):
            raise RuntimeError, 'component {0} does not support command {1}'.format(component,command)
        return getattr(self._components[component],command)(**kwds)

    def run(self):
        """processing loop

        check task queues of the controllers, if they contain a task run it and
        pass results back to the controller's done queue"""
        done = False
        while True:
            waitALittle = True
            for tq,dq in self._clients:
                if not tq.empty():
                    task = tq.get()
                    waitALittle = False

                    if task[0] == 'stop':
                        done = True
                    elif task[0] == 'components':
                        dq.put(('ok',self.getComponentList()))
                    else:
                        try:
                            result = 'ok',self.invoke(task[1],task[0],task[2])
                        except:
                            result = 'nok',sys.exc_info()[1].message
                        dq.put(result)
            if waitALittle:
                if done:
                    # tell components to stop
                    for c in self._components:
                        self.invoke(c,'stop')
                    # tell all clients that the system has stopped
                    for tq,dq in self._clients:
                        dq.put(('ok','stopped'))
                    return
                time.sleep(self.DELAY)
