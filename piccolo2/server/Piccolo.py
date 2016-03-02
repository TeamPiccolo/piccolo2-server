"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['Piccolo']

from PiccoloInstrument import PiccoloInstrument
import socket
import psutil
import subprocess
import datetime

class Piccolo(PiccoloInstrument):
    """piccolo server instrument

    the piccolo server itself is treated as an instrument"""

    def info(self):
        """get info

        :returns: dictionary containing system information
        :rtype: dict"""
        self.log.debug("info")
        info = {'hostname':  socket.gethostname(),
                'cpu_percent': psutil.cpu_percent(),
                'virtual_memory': dict(psutil.virtmem_usage()._asdict())}
        return info

    def getClock(self):
        """get the current date and time

        :returns: isoformat date and time string"""
        return datetime.datetime.now().isoformat()

    def setClock(self,clock=None):
        """set the current date and time

        :param clock: isoformat date and time string used to set the time"""
        if clock!=None:
            cmdPipe = subprocess.Popen(['date','-s',clock],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            if cmdPipe.wait()!=0:
                raise OSError, 'setting date to \'{}\': {}'.format(clock,cmdPipe.stderr.read())
            return cmdPipe.stdout.read()
        return ''
        

if __name__ == '__main__':
    from piccoloLogging import *

    piccoloLogging(debug=True)
    p = Piccolo("piccolo")
    print p.ping()
    print p.status()
    print p.info()
    print p.getClock()
