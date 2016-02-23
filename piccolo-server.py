import piccolo
import time

class PiccoloDispatcher(object):

    DELAY = 1
    
    def __init__(self):
        self._components = {}
        self._clients = []

    def registerComponent(self,name,component):
        self._components[name] = component

    def registerController(self,taskQ,doneQ):
        self._clients.append((taskQ,doneQ))
        
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
                        dq.put('stopped')
                        done = True
                    elif task[0] == 'components':
                        dq.put(self.getComponentList())
                    else:
                        dq.put(self._execute(task[0],task[1],task[2]))
            if waitALittle:
                if done:
                    for c in self._components:
                        self._execute(c,'stop')
                    return
                time.sleep(self.DELAY)

if __name__ == '__main__':
    import Queue
    
    pd = PiccoloDispatcher()
    pd.registerComponent('piccolo',piccolo.Piccolo())
    print pd.getComponentList()
    print pd._execute('piccolo','ping')

    taskQ = Queue.Queue()
    doneQ = Queue.Queue()

    pd.registerController(taskQ,doneQ)

    taskQ.put(('components',None,{}))
    taskQ.put(('piccolo','ping',{}))
    taskQ.put(('stop',None,{}))

    pd.run()

    print
    print 'processing queue'
    while True:
        d = doneQ.get()
        print d
        if d=='stopped':
            break
        
