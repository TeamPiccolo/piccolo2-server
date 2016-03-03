"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['Piccolo']

from PiccoloInstrument import PiccoloInstrument
from PiccoloDataDir import PiccoloDataDir
import socket
import psutil
import subprocess
import datetime

class Piccolo(PiccoloInstrument):
    """piccolo server instrument

    the piccolo server itself is treated as an instrument"""

    def __init__(self,name,datadir):
        """
        :param name: name of the component
        :param datadir: data directory
        :type datadir: PiccoloDataDir"""

        assert isinstance(datadir,PiccoloDataDir)
        PiccoloInstrument.__init__(self,name)
        self._datadir = datadir

    def info(self):
        """get info

        :returns: dictionary containing system information
        :rtype: dict"""
        self.log.debug("info")
        info = {'hostname':  socket.gethostname(),
                'cpu_percent': psutil.cpu_percent(),
                'virtual_memory': dict(psutil.virtmem_usage()._asdict())}
        if self._datadir.isMounted:
            info['datadir'] = self._datadir.datadir
        else:
            info['datadir'] = 'not mounted'
        return info

    def getClock(self):
        """get the current date and time

        :returns: isoformat date and time string"""
        return datetime.datetime.now().isoformat()

    def setClock(self,clock=None):
        """set the current date and time

        :param clock: isoformat date and time string used to set the time"""
        if clock!=None:
            cmdPipe = subprocess.Popen(['sudo','date','-s',clock],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            if cmdPipe.wait()!=0:
                raise OSError, 'setting date to \'{}\': {}'.format(clock,cmdPipe.stderr.read())
            return cmdPipe.stdout.read()
        return ''
        
    def isMountedDataDir(self):
        """check if datadir is mounted"""
        return self._datadir.isMounted

    def mountDatadir(self):
        """attempt to mount datadir"""
        self._datadir.mount()
        return 'ok'

    def umountDatadir(self):
        """attempt to unmount datadir"""
        self._datadir.umount()
        return 'ok'


if __name__ == '__main__':
    from piccoloLogging import *

    piccoloLogging(debug=True)
    p = Piccolo("piccolo")
    print p.ping()
    print p.status()
    print p.info()
    print p.getClock()
