"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>
"""

__all__ = ['PiccoloWorkerThread']

import threading
from Queue import Queue
import logging

class PiccoloWorkerThread(threading.Thread):
    """base piccolo worker thread object"""

    LOGNAME = None

    def __init__(self,name,busy,tasks,results,daemon=True):
        assert isinstance(tasks,Queue)
        assert isinstance(results,Queue)

        threading.Thread.__init__(self)
        self.name = name
        self.daemon = daemon

        self._log = logging.getLogger('piccolo.worker.{0}.{1}'.format(self.LOGNAME,name))
        self.log.info('initialising worker')

        self._busy = busy
        self._tQ = tasks
        self._rQ = results

    @property
    def log(self):
        return self._log

    @property
    def busy(self):
        return self._busy

    @property
    def tasks(self):
        return self._tQ
    @property
    def results(self):
        return self._rQ

    def run(self):
        raise NotImplementedError
