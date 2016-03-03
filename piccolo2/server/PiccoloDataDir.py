"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloDataDir']

import subprocess
import os, os.path
import logging

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
    

if __name__ == '__main__':
    from piccoloLogging import *

    piccoloLogging(debug=True)

    t = PiccoloDataDir('/dev/shm/ptest')
    print t.datadir
    t2 = PiccoloDataDir('ptest')
    print t2.datadir
    t3 = PiccoloDataDir('ptest',mount=True)
    print t3.datadir
