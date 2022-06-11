# coding=utf-8
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from app.models import JobList

logger = logging.getLogger(__name__)


def start_scheduler():
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()


class JobAction:
    def __init__(self):
        self.scheduler = scheduler
        self.scheduler.add_listener(self.my_listener, EVENT_JOB_ERROR | EVENT_JOB_MISSED | EVENT_JOB_EXECUTED)

    @staticmethod
    def start_date_job(trigger, job_rate, id):
        exec(JobList.objects.get(id=id).trigger.func_path)
        trigger_id = trigger + '-' + id
        scheduler.add_job(eval(trigger), 'date', run_date=job_rate, id=trigger_id, args=[trigger_id, id, 'date'])
        logger.info("%s start successfully" % trigger)
        logger.info('任务池：' + str(scheduler.get_jobs))

    @staticmethod
    def start_cron_job(trigger, job_rate, id):
        exec(JobList.objects.get(id=id).trigger.func_path)
        rate = job_rate.split()
        trigger_id = trigger + '-' + id
        # 秒 分 时 日 月 星期 年
        scheduler.add_job(eval(trigger), 'cron', second=rate[0], minute=rate[1], hour=rate[2], day=rate[3],
                          month=rate[4], day_of_week=rate[5], year=rate[6], id=trigger_id,
                          args=[trigger_id, id, 'cron'])
        logger.info("%s start successfully" % trigger)
        logger.info('任务池：' + str(scheduler.get_jobs))

    # 停止任务
    @staticmethod
    def stop_job(trigger_id):
        if scheduler.get_job(trigger_id):
            scheduler.remove_job(trigger_id)
            logger.info('已启动的任务：' + str(scheduler.get_jobs()))

    # 暂停任务
    @staticmethod
    def pause_job(trigger_id):
        logger.info(trigger_id)
        scheduler.pause_job(trigger_id)

    # 重启任务
    @staticmethod
    def resume_job(trigger_id):
        scheduler.resume_job(trigger_id)

    # 修改任务
    @staticmethod
    def modify_job(trigger_id, job_value):
        if job_value[0] == 'cron':
            rate = job_value[1].split()
            scheduler.reschedule_job(trigger_id, trigger='cron', second=rate[0], minute=rate[1],
                                     hour=rate[2], day=rate[3], month=rate[4], day_of_week=rate[5], year=rate[6])
        elif job_value[0] == 'date':
            scheduler.reschedule_job(trigger_id, trigger='date', run_date=job_value[1])

    @staticmethod
    def my_listener(event):  # 添加监听器
        job = scheduler.get_job(event.job_id)
        if not event.exception:
            pass
        else:
            logger.error("jobname=%s|jobtrigger=%s|errcode=%s|exception=[%s]|traceback=[%s]|scheduled_time=%s",
                         job.name, job.trigger, event.code, event.exception, event.traceback, event.scheduled_run_time)
        # scheduler.shutdown(wait=False)
