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
