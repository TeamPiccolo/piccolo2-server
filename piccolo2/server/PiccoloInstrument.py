"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloInstrument']


class PiccoloInstrument(object):
    """base class used to define instruments attached to the piccolo system
    """

    def __init__(self,name):
        """
        :param name: name of the component"""
        self._name = name

    @property
    def name(self):
        """the name of the component"""
        return self._name

    def ping(self):
        """ping instrument

        :return: *pong*"""
        
        return 'pong'

    def status(self):
        """get instrument status

        :return: *ok*"""
        return 'ok'

    def stop(self):
        """stop instrument"""
        return 'ok'

if __name__ == '__main__':

    p = PiccoloInstrument("test")
    print p.ping()
    print p.status()
