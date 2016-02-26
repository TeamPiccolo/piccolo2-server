"""
.. moduleauthor:: Magnus Hagdorn <magnus.hagdorn@ed.ac.uk>

"""

__all__ = ['PiccoloDispatcher']

import logging
import threading
import time
import sys
from PiccoloInstrument import PiccoloInstrument
from PiccoloController import PiccoloController
from PiccoloScheduler import PiccoloScheduler

class PiccoloDispatcher(threading.Thread):
    """piccolo dispatcher class
    
    The dispatcher sits at the centre and takes instructions from the
    controllers and passes them on to the instruments. 
    """

    DELAY = 0.1
    
    def __init__(self,daemon=False):
        """
        :param daemon: whether the dispatcher thread should be daemonised. When
                       set to true, the dispatcher thread stops when the main
                       thread stops. default False
        :type daemon: logical"""
        threading.Thread.__init__(self,name="PiccoloDispatcher")

        self.daemon = daemon
        self._components = {}
        self._clients = []
        self._scheduler = PiccoloScheduler()

        self._log = logging.getLogger('piccolo.dispatcher')

        self.log.info("initialised")

    @property
    def log(self):
        """get the logger"""
        return self._log

    def registerComponent(self,component):
        """register a component, ie instrument

        :param component: the instance of a piccolo instrument
        :type component: PiccoloInstrument"""
        self.log.info('registering component {0}'.format(component.name))
        assert isinstance(component,PiccoloInstrument)
        self._components[component.name] = component

    def registerController(self,controller):
        """register a controller
        
        :param controller: instance of a controller
        :type controller: PiccoloController"""
        #assert isinstance(controller,PiccoloController)
        self._clients.append((controller.taskQ,controller.doneQ))
        
    def getComponentList(self):
        """get list of registered components
        :returns: list of components"""
        return self._components.keys()

    def invoke(self,component,command,kwds={}):
        """run command on a component

        :param component: the name of the component to run command on
        :param command: the command to run
        :param kwds: dictionary containing command parameters
        :returns: result of running command"""

        self.log.debug('invoke {0} {1}'.format(component,command))

        if component not in self._components:
            raise KeyError, 'unkown component {0}'.format(component)
        if not hasattr(self._components[component],command):
            raise RuntimeError, 'component {0} does not support command {1}'.format(component,command)
        return getattr(self._components[component],command)(**kwds)

    def _runTask(self,task):
        """run a task
        :param task: task tuple (command,component,kwds)
        :return: (status,result) where status is 'ok' or 'nok'
        """
        try:
            result = 'ok',self.invoke(task[1],task[0],task[2])
        except:
            self.log.error('{0} {1}: {2}'.format(task[1],task[0],sys.exc_info()[1].message))
            result = 'nok',sys.exc_info()[1].message
        return result        

    def run(self):
        """processing loop

        check task queues of the controllers, if they contain a task run it and
        pass results back to the controller's done queue"""
        done = False
        schedule = {}
        while True:
            waitALittle = True
            # execute any scheduled jobs
            for job in self._scheduler.runable_jobs:
                task = job.run()
                self.log.info("running scheduled job {0}: {1} {2}".format(job.jid,task[0],task[1]))
                result = self._runTask(task)

            # check for new tasks and run/schedule them
            for tq,dq in self._clients:
                if not tq.empty():
                    task = tq.get()
                    waitALittle = False

                    if task[0] == 'stop':
                        self.log.info("about to stop")
                        done = True
                    elif task[0] == 'components':
                        dq.put(('ok',self.getComponentList()))
                    else:
                        # intercept any schedule instructions
                        for s in ['at_time','interval','end_time']:
                            if s in task[2]:
                                schedule[s] = task[2][s]
                                del task[2][s]
                            else:
                                schedule[s] = None
                        if schedule['at_time']!=None:
                            self.log.info("scheduling {0} {1} at {2}:{3}:{4}".format(task[0],task[1],schedule['at_time'],schedule['interval'],schedule['end_time']))
                            try:
                                self._scheduler.add(schedule['at_time'],task,interval=schedule['interval'],end_time=schedule['end_time'])
                                result = ('ok','scheduled')
                            except:
                                self.log.error('error scheduling {0} {1}: {2}'.format(task[1],task[0],sys.exc_info()[1].message))
                                result = 'nok',sys.exc_info()[1].message
                        else:
                            result = self._runTask(task)
                        dq.put(result)
            if waitALittle:
                if done:
                    # tell components to stop
                    for c in self._components:
                        self.invoke(c,'stop')
                    # tell all clients that the system has stopped
                    for tq,dq in self._clients:
                        dq.put(('ok','stopped'))
                    return
                time.sleep(self.DELAY)
