from django.core.cache import cache

from app.models import JobList
import logging

logger = logging.getLogger(__name__)


def job_before(func):
    def wrapper(*args, **kwargs):
        from app.job_new import JobAction
        job_state = JobList.objects.filter(id=int(args[1])).values('job_state')[0]['job_state']
        if job_state == 1:
            job_value = cache.get(args[0])
            if job_value:
                JobAction.modify_job(args[0], job_value)
                cache.delete(args[0])
            if get_lock(args[0]):
                if args[2] == 'date' or (job_value and job_value[0] == 'date'):
                    JobList.objects.filter(id=int(args[1])).update(job_state=0)
                func(*args, **kwargs)
            else:
                logger.info('该线程未取到锁，停止该任务！')
                JobAction.stop_job(args[0])
        else:
            JobAction.stop_job(args[0])

    return wrapper


def get_lock(lock_name):
    lock = cache.lock('lock.' + lock_name, timeout=5)
    return lock.acquire(blocking=False)
