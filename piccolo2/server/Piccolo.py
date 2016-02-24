__all__ = ['Piccolo']

from PiccoloInstrument import PiccoloInstrument
import socket
import psutil

class Piccolo(PiccoloInstrument):
    def info(self):
        info = {'hostname':  socket.gethostname(),
                'cpu_percent': psutil.cpu_percent(),
                'virtual_memory': dict(psutil.virtual_memory()._asdict())}
        return info

if __name__ == '__main__':
    p = Piccolo()
    print p.ping()
    print p.status()
    print p.info()
