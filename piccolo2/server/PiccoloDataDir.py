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

__all__ = ['PiccoloDataDir']

import subprocess
import os, os.path, glob
import logging

def cmpMtimes(f1,f2):
    if os.path.getmtime(f1) < os.path.getmtime(f2):
        return -1
    elif os.path.getmtime(f1) > os.path.getmtime(f2):
        return 1
    else:
        return 0

class PiccoloDataDir(object):
    """manage piccolo output data directory"""
    def __init__(self,datadir,device='/dev/sda1',mntpnt='/mnt',mount=False):
        """
        :param datadir: the data directory. If the path is not absolute then either append datadir to the mount point if mount==True or to the current working directory
        :param device: block device that should get mounted if mount==True
        :param mntpnt: the mount point where the device should get mounted
        :param mount: attempt to mount (requires sudo) device
        """

        self._log = logging.getLogger('piccolo.datadir')
        self.log.info("initialising datadir {}".format(datadir))
        if mount:
            self.log.info("with device {} mounted at {}".format(device,mntpnt))

        self._mount = mount
        self._device = device
        if mntpnt.endswith(os.sep):
            self._mntpnt = mntpnt[:-1]
        else:
            self._mntpnt = mntpnt

        if self._mount:
            self.mount()
            self._datadir = os.path.join(self._mntpnt,datadir)
        else:
            if datadir.startswith(os.sep):
                self._datadir = datadir
            else:
                self._datadir = os.path.join(os.getcwd(),datadir)

    @property
    def log(self):
        """get the log"""
        return self._log

    @property
    def datadir(self):
        """perform checks and create data directory if necessary

        :return: data directory"""
        if self._mount and not self.isMounted:
            raise RuntimeError, '{} not mounted at {}'.format(self._device,self._mntpnt)
        if not os.path.exists(self._datadir):
            self.log.info("creating data directory {}".format(self._datadir))
            os.makedirs(self._datadir)
        if not os.path.isdir(self._datadir):
            raise RuntimeError, '{} is not a directory'.format(self._datadir)
        if not os.access(self._datadir,os.W_OK):
            raise RuntimeError, 'cannot write to {}'.format(self._datadir)
        return self._datadir
        
    @property
    def isMounted(self):
        """:return: True if the device is mounted at the correct mount point
                    False if the device is not mounted
                    raises a RuntimeError if the device is mounted at the wrong
                    mount point"""
        with open('/proc/mounts', 'r') as mnt:
            for line in mnt.readlines():
                fields = line.split()
                if fields[0] == self._device:
                    if fields[1] == self._mntpnt:
                        return True
                    raise RuntimeError, "device {} mounted in wrong directory {}".format(self._device,fields[1])
            return False
        raise OSError, "Cannot read /proc/mounts"


    def mount(self):
        """attempt to mount device at mount point"""

        if not self._mount:
            raise RuntimeError, "not setup to mount {} at {}".format(self._device,self._mntpnt)
        if not self.isMounted:
            self.log.info("mounting {} at {}".format(self._device,self._mntpnt))
            cmdPipe = subprocess.Popen(['sudo','mount','-o','uid={},gid={}'.format(os.getuid(),os.getgid()),
                                        self._device,self._mntpnt],stderr=subprocess.PIPE)
            if cmdPipe.wait()!=0:
                raise OSError, 'mounting {} at {}: {}'.format(self._device,self._mntpnt, cmdPipe.stderr.read())
            
    def umount(self):
        """attempt to umount device at mount point"""

        if not self._mount:
            raise RuntimeError, "not setup to mount {} at {}".format(self._device,self._mntpnt)
        if self.isMounted:
            self.log.info("unmounting {}".format(self._device))
            cmdPipe = subprocess.Popen(['sudo','umount',self._device],stderr=subprocess.PIPE)
            if cmdPipe.wait()!=0:
                raise OSError, 'unmounting {}: {}'.format(self._device, cmdPipe.stderr.read())

    def getFileList(self,path,pattern='*.pico*',haveNFiles=0):
        p = self.join(path)
        fullList = glob.glob(os.path.join(p,pattern))
        fullList.sort(cmpMtimes)
        fileList = []
        for f in fullList:
            fileList.append(os.path.relpath(f,self.datadir))
        return fileList[haveNFiles:]

    def getNextCounter(self,path,pattern='*.pico*'):
        nextCounter = 0
        for f in self.getFileList(path,pattern):
            f = os.path.basename(f).split('_')[0]
            try:
                # start after first character because file name starts with a b
                m = int(f[1:])
            except:
                continue
            nextCounter = max(nextCounter,m)
        if nextCounter>0:
            nextCounter = nextCounter + 1
        return nextCounter
    
    def getFileData(self,fname):
        return open(self.join(fname),'r').read()

    def join(self,p):
        """join path to datadir if path is not absolute

        :param p: path to be joined"""

        if not os.path.isabs(p):
            return os.path.join(self.datadir,p)
        return p
    

if __name__ == '__main__':
    from piccoloLogging import *

    piccoloLogging(debug=True)

    t = PiccoloDataDir('/dev/shm/ptest')
    print t.datadir
    t2 = PiccoloDataDir('ptest')
    print t2.datadir
    t3 = PiccoloDataDir('ptest',mount=True)
    print t3.datadir

    print t3.join('test')
