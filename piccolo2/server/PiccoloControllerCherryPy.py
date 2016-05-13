# Copyright 2014-2016 The Piccolo Team
#
# This file is part of piccolo2-server.
#
# piccolo2-server is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# piccolo2-server is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with piccolo2-server.  If not, see <http://www.gnu.org/licenses/>.

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
    
