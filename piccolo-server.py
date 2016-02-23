import piccolo
import time

class PiccoloDispatcher(object):

    DELAY = 1
    
    def __init__(self):
        self._components = {}
        self._clients = []

    def registerComponent(self,name,component):
        assert isinstance(component,piccolo.PiccoloInstrument)
        self._components[name] = component

    def registerController(self,controller):
        assert isinstance(controller,piccolo.PiccoloController)
        self._clients.append((controller.taskQ,controller.doneQ))
        
    def getComponentList(self):
        return self._components.keys()

    def _execute(self,name,command,kwds={}):
        if name not in self._components:
            raise KeyError, 'unkown component {0}'.format(name)
        if not hasattr(self._components[name],command):
            raise RuntimeError, 'component {0} does not support command {1}'.format(name,command)
        return getattr(self._components[name],command)(**kwds)

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
                        dq.put(self.getComponentList())
                    else:
                        dq.put(self._execute(task[0],task[1],task[2]))
            if waitALittle:
                if done:
                    # tell components to stop
                    for c in self._components:
                        self._execute(c,'stop')
                    # tell all clients that the system has stopped
                    for tq,dq in self._clients:
                        dq.put('stopped')
                    return
                time.sleep(self.DELAY)

if __name__ == '__main__':
    
    pd = PiccoloDispatcher()
    pd.registerComponent('piccolo',piccolo.Piccolo())
    print pd.getComponentList()
    print pd._execute('piccolo','ping')

    pc = piccolo.PiccoloController()

    pd.registerController(pc)

    pc.taskQ.put(('components',None,{}))
    pc.taskQ.put(('piccolo','ping',{}))
    pc.taskQ.put(('stop',None,{}))

    pd.run()

    print
    print 'processing queue'
    while True:
        d = pc.doneQ.get()
        print d
        if d=='stopped':
            break
        
