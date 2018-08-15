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

import os
import threading
from Queue import Queue
import logging
import sqlite3
from piccolo2.common import PiccoloWorkerThread

class PiccoloMessagesWorker(PiccoloWorkerThread):
    LOGNAME = 'messageBackend'

    def __init__(self,dbName, busy,tasks, results):
        
        PiccoloWorkerThread.__init__(self, "PiccoloMessageBackend", busy, tasks, results)

        self._dbName = dbName
                
    def run(self):
        conn = sqlite3.connect(self._dbName)
        cur = conn.cursor()
        # tidy away existing tables
        cur.execute("drop table if exists messages;")
        cur.execute("drop table if exists listeners;")
        # create tables
        cur.execute("create table messages (msgid integer primary key, msg text);")
        cur.execute("create table listeners (listener integer primary key, last integer);")

        current_msg = 0
        current_listener = 0

        while True:
            # wait for a new task from the task queue
            task = self.tasks.get()
            if task == None:
                # The worker thread can be stopped by putting a None onto the task queue.
                self.log.info('Stopped worker thread for specrometer {}.'.format(self.name))
                return
            self.busy.acquire()
            
            if task[0] == 'new':
                newID = current_listener
                cur.execute("insert into listeners values (?,?)",(newID,current_msg))
                conn.commit()
                current_listener += 1
                self.results.put(newID)
            elif task[0] == 'status':
                cur.execute("select last from listeners where listener = ?;",(task[1],))
                res = cur.fetchone()
                if res is None:
                    self.results.put(False)
                else:
                    self.results.put(res[0] < current_msg)
            elif task[0] == 'remove':
                cur.execute("delete from listeners where listener = ?;",(task[1],))
                conn.commit()
            elif task[0] == 'add':
                cur.execute("insert into messages values (?,?);",(current_msg,task[1]))
                conn.commit()
                current_msg += 1
            elif task[0] == 'get':
                msg = ''
                cur.execute("select last from listeners where listener = ?;",(task[1],))
                res = cur.fetchone()
                if res is not None and res[0] < current_msg:
                    msgid = res[0]
                    cur.execute("select msg from messages where msgid = ?;",(msgid,))
                    res = cur.fetchone()
                    if res is not None:
                        msg = res[0]
                    cur.execute("update listeners set last = ? where listener = ?;",(msgid+1,task[1]))
                    conn.commit()
                self.results.put(msg)

                # tidy away old messages
                cur.execute("select min(last) from listeners;")
                res = cur.fetchone()
                if res is not None:
                    cur.execute("delete from messages where msgid < ?;",(res[0],))
                    conn.commit()

            self.busy.release()
                
class PiccoloMessages(object):
    def __init__(self,dbName=None):

        if dbName is None:
            uid = os.getuid()
            if uid == 0:
                dbName = '/var/run/piccolo_msg.sqlite'
            else:
                dbName = '/var/run/user/%d/piccolo_msg.sqlite'%uid

        self._busy = threading.Lock()
        self._tQ = Queue() # Task queue.
        self._rQ = Queue() # Results queue.

        self._messages = PiccoloMessagesWorker(dbName,self._busy,self._tQ,self._rQ)
        self._messages.start()

    def __del__(self):
        # send poison pill to worker
        self._tQ.put(None)
        self._messages.join()

    def newListener(self):
        self._tQ.put(('new',))
        return self._rQ.get()

    def removeListener(self,listener):
        self._tQ.put(('remove',listener))
    
    def addMessage(self,message):
        self._tQ.put(('add',message))

    def warning(self,message):
        self.addMessage('warning|%s'%message)
            
    def error(self,message):
        self.addMessage('error|%s'%message)
            
    def status(self,listener):
        self._tQ.put(('status',listener))
        return self._rQ.get()

    def getMessage(self,listener):
        self._tQ.put(('get',listener))
        return self._rQ.get()

if __name__ == '__main__':
    messages = PiccoloMessages(dbName="/tmp/test.sqlite")

    lid = messages.newListener()
    #lid2 = messages.newListener()

    messages.addMessage("hello world")
    messages.warning("this is a warning")
    messages.error("this is an error")
                     
    for i in range(2):
        msg = messages.getMessage(lid)
        print msg
        if msg == '':
            break
    
    
