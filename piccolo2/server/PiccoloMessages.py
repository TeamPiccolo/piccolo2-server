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

__all__ = ['PiccoloMessages']

class PiccoloMessages(object):
    def __init__(self):
        self._curID = 0
        self._messages = {}

    def newListener(self):
        newID = self._curID
        self._messages[newID] = set()
        self._curID = self._curID+1
        return newID

    def removeListener(self,listener):
        del self._messages[listener]
    
    def addMessage(self,message):
        for l in self._messages:
            self._messages[l].add(message)

    def status(self,listener):
        return len(self._messages[listener])>0

    def getMessage(self,listener):
        if self.status(listener):
            return self._messages[listener].pop()
        else:
            return ''
