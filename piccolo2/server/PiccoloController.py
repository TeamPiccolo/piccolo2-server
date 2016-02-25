
"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloController']

import Queue

class PiccoloController(object):
    """piccolo controller base class

    The Piccolo Controller takes instructions from some source and passes them
    on to the dispatcher. Communication is done via queues"""
    def __init__(self):
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

    def components(self):
        """get a list of components"""
        return self.invoke('components')

    def stop(self):
        return self.invoke('stop')

    def invoke(self,command,component=None,keywords={}):
        """call a piccolo command

        :param command: the command to run
        :param component: the name of the component the command should run on (can be None)
        :param keywords: any keywords that should be passed to command
        :return: tuple containing the status and result

        a command is scheduled by appending to the task queue, the system 
        waits until the result appears in the done queue
        """
        
        self._taskQ.put((command,component,keywords))
        return self._doneQ.get()

    def __getattr__(self,name):
        def func(component,**keywords):
            return self.invoke(name,component=component,keywords=keywords)
        return func

