__all__ = ['PiccoloController']

import Queue

class PiccoloController(object):
    def __init__(self):
        self._taskQ = Queue.Queue()
        self._doneQ = Queue.Queue()
    
    @property
    def taskQ(self):
        return self._taskQ

    @property
    def doneQ(self):
        return self._doneQ

    def components(self):
        return self.call('components')

    def stop(self):
        return self.call('stop')

    def invoke(self,command,component=None,keywords={}):
        self._taskQ.put((command,component,keywords))
        return self._doneQ.get()

    def __getattr__(self,name):
        def func(component,**keywords):
            return self.invoke(name,component=component,keywords=keywords)
        return func

