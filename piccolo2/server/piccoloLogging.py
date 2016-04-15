__all__ = ["piccoloLogging"]

import logging

def piccoloLogging(logfile = None,debug=False):
    """setup logging

    :param logfile: name of logfile - log to stdout if None
    :param debug: setlog level to debug
    :type debug: logical"""

    log = logging.getLogger("piccolo")

    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    if logfile == None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(logfile)

    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(name)s: %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

    return handler
