__all__ = ['PiccoloDispatcher']

import threading
import time
import sys
from PiccoloInstrument import PiccoloInstrument
from PiccoloController import PiccoloController

class PiccoloDispatcher(threading.Thread):

    DELAY = 0.1
    
    def __init__(self,daemon=False):
        threading.Thread.__init__(self,name="PiccoloDispatcher")

        self.daemon = daemon
        self._components = {}
        self._clients = []

    def registerComponent(self,name,component):
        assert isinstance(component,PiccoloInstrument)
        self._components[name] = component

    def registerController(self,controller):
        #assert isinstance(controller,PiccoloController)
        self._clients.append((controller.taskQ,controller.doneQ))
        
    def getComponentList(self):
        return self._components.keys()

    def _execute(self,component,command,kwds={}):
        if component not in self._components:
            raise KeyError, 'unkown component {0}'.format(component)
        if not hasattr(self._components[component],command):
            raise RuntimeError, 'component {0} does not support command {1}'.format(component,command)
        return getattr(self._components[component],command)(**kwds)

    def run(self):
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
                            result = 'ok',self._execute(task[1],task[0],task[2])
                        except:
                            result = 'nok',sys.exc_info()[1].message
                        dq.put(result)
            if waitALittle:
                if done:
                    # tell components to stop
                    for c in self._components:
                        self._execute(c,'stop')
                    # tell all clients that the system has stopped
                    for tq,dq in self._clients:
                        dq.put(('ok','stopped'))
                    return
                time.sleep(self.DELAY)
