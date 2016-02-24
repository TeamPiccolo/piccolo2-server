__all__ = ['PiccoloControllerCherryPy']

import cherrypy
from pyjsonrpc.cp import CherryPyJsonRpc, rpcmethod
import Queue

class PiccoloControllerCherryPy(CherryPyJsonRpc):
    def __init__(self):
        CherryPyJsonRpc.__init__(self)
        self._taskQ = Queue.Queue()
        self._doneQ = Queue.Queue()

    @property
    def taskQ(self):
        return self._taskQ

    @property
    def doneQ(self):
        return self._doneQ

    @rpcmethod
    def invoke(self,command,component=None,keywords={}):
        self._taskQ.put((command,component,keywords))
        return self._doneQ.get()

    index = CherryPyJsonRpc.request_handler
    
