__all__ = ['PiccoloInstrument']


class PiccoloInstrument(object):

    def __init__(self):
        pass

    def ping(self):
        return 'pong'

    def status(self):
        return 'ok'

    def stop(self):
        return 'ok'

if __name__ == '__main__':

    p = PiccoloInstrument()
    print p.ping()
    print p.status()
