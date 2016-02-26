__all__ = ['PiccoloScheduledJob','PiccoloScheduler']

import logging
import datetime

class PiccoloScheduledJob(object):
    """a scheduled job

    a job will only get scheduled if it is in the future
    """

    def __init__(self,at_time,interval,job,end_time=None,jid=-1):
        """
        :param at_time: the time at which the job should run
        :type at_time: datetime.datetime
        :param interval: repeated schedule job if interval is not set to None
        :type interval: datetime.timedelta
        :param job: scheduled job object, gets returned when run method is called
        :param end_time: the time after which the job is no longer scheduled
        :type end_time: datetime.datetime or None
        :param jid: an ID
        :type jid: int
        """
        
        self._log = logging.getLogger('piccolo.scheduledjob')

        assert isinstance(at_time,datetime.datetime)
        if interval!=None:
            assert isinstance(interval,datetime.timedelta)
        if end_time!=None:
            assert isinstance(end_time,datetime.datetime)

        self._jid = jid
        self._at = at_time
        self._end = end_time
        self._interval = interval
        self._job = job
        self._has_run = False
        self._suspended = False

        # check that scheduled time is not in the past
        if self._at < datetime.datetime.now():
            self.log.warning("scheduled job is in the past")
            self._has_run = True
        if self._end!= None and self._at >= self._end:
            self.log.warning("job is scheduled for execution after the end time")
            self._has_run = True


    @property
    def log(self):
        """get the logger"""
        return self._log

    @property
    def jid(self):
        """get the ID"""
        return self._jid

    @property
    def shouldRun(self):
        """:return: True if the job has not already run and the scheduled time 
                    < now
        """
        if self._has_run or self.suspended:
            return False
        else:
            return self._at < datetime.datetime.now()

    @property
    def suspended(self):
        """whether the job is suspended"""
        return self._suspended

    @property
    def at_time(self):
        """ the time at which the job should run"""
        return self._at

    @property
    def end_time(self):
        """get time after which the job should not be run anymore"""
        return self._end

    @property
    def interval(self):
        """the interval at which the job should be repeated or None for a single job"""
        return self._interval
        
    def __lt__(self,other):
        assert isinstance(other,PiccoloScheduledJob)
        return self.at_time < other.at_time

    def suspend(self,suspend=True):
        """suspend job"""
        self._suspended = suspend

    def unsuspend(self,suspend=False):
        """unsuspend job"""
        self._suspended = suspend        

    def run(self):
        """run the job

        check if the job should be run, increment scheduled time if applicable"""
        if not self.shouldRun:
            return None
        if self._interval == None:
            self.log.debug("final run of job {0}".format(self.jid))
            self._has_run = True
        else:
            n = (datetime.datetime.now()-self._at).total_seconds()//self._interval.total_seconds()+1
            if n>1:
                self.log.debug("job {0}: fast forwarding {1} times".format(self.jid,n))
                dt = datetime.timedelta(seconds=n*self._interval.total_seconds())
            else:
                dt = self._interval
            self._at = self._at + dt
            self.log.debug("job {0}: incrementing scheduled time".format(self.jid))
            if self._end!= None and self._at >= self._end:
                self._has_run = True
                self.log.debug("job {0}: new time is beyond end time".format(self.jid))

        return self._job

class PiccoloScheduler(object):
    """the piccolo scheduler holds the scheduled jobs"""
    def __init__(self):
        self._log = logging.getLogger('piccolo.scheduler')
        self._jobs = []

    def add(self,at_time,job,interval=None,end_time=None):
        """add a new job

        :param at_time: the time at which the job should run
        :type at_time: datetime.datetime
        :param job: object returned when scheduled job is run
        :param interval: repeated schedule job if interval is not set to None
        :type interval: datetime.timedelta
        :param end_time: the time after which the job is no longer scheduled
        :type end_time: datetime.datetime or None
        """

        jid = len(self._jobs)

        job = PiccoloScheduledJob(at_time,interval,job,end_time=end_time,jid=jid)

        self._jobs.append(job)
        self._jobs.sort()

    @property
    def runable_jobs(self):
        """get iterator over runable jobs"""
        return (job for job in self._jobs if job.shouldRun)

    @property
    def jobs(self):
        """get iterator over all jobs"""
        for job in self._jobs:
            yield job

    def _suspend(self,jid,state):
        """suspend or unsuspend particular job"""

        for job in self._jobs:
            if job.jid == jid:
                job.suspend(suspend=state)
                return
        raise LookupError, 'unknown jid {0}'.format(jid)

    def suspend(self,jid):
        """suspend job
        
        :param jid: id of job to suspend
        :type jid: int"""
        self._suspend(jid,True)

    def unsuspend(self,jid):
        """unsuspend job
        
        :param jid: id of job to unsuspend
        :type jid: int"""
        self._suspend(jid,False)
   
if __name__ == '__main__':
    from piccoloLogging import *
    import time

    piccoloLogging(debug=True)

    ps = PiccoloScheduler()
    
    ps.add(datetime.datetime.now()+datetime.timedelta(seconds=5),"hello")
    ps.add(datetime.datetime.now()+datetime.timedelta(seconds=10),"hello2",interval=datetime.timedelta(seconds=5))
    ps.add(datetime.datetime.now()+datetime.timedelta(seconds=8),"hello3",interval=datetime.timedelta(seconds=3),end_time=datetime.datetime.now()+datetime.timedelta(seconds=20))

    ps.add(datetime.datetime.now()-datetime.timedelta(seconds=5),"this should not be scheduled as in the past")

    for i in range(0,100):
        for job in ps.runable_jobs:
            print job.jid, job.at_time, job.run()
        time.sleep(1)
        if i==27:
            ps.suspend(1)
        if i==41:
            ps.unsuspend(1)
        print i
