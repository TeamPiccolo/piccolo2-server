"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloControllerCherryPy']

import cherrypy
from pyjsonrpc.cp import CherryPyJsonRpc, rpcmethod
import Queue

class PiccoloControllerCherryPy(CherryPyJsonRpc):
    """piccolo controller using JSON RPC and CherryPy

    .. note:: this re-implements some methods of the base controller as I could
              not get multiple inheritance to work"""
    def __init__(self):
        CherryPyJsonRpc.__init__(self)
        self._taskQ = Queue.Queue()
        self._doneQ = Queue.Queue()

    @property
    def taskQ(self):
        """the task queue"""
        return self._taskQ

    @property
    def doneQ(self):
        """the done queue"""
        return self._doneQ

    @rpcmethod
    def invoke(self,command,component=None,keywords={}):
        """call a piccolo command

        :param command: the command to run
        :param component: the name of the component the command should run on 
                          (can be None)
        :param keywords: any keywords that should be passed to command
        :return: tuple containing the status and result

        a command is scheduled by appending to the task queue, the system 
        waits until the result appears in the done queue
        """

        self._taskQ.put((command,component,keywords))
        return self._doneQ.get()

    index = CherryPyJsonRpc.request_handler
    
