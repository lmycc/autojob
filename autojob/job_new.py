# coding=utf-8
import logging
import os
import re
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from autojob.models import JobList

logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def start_scheduler():
    global scheduler
    scheduler = BackgroundScheduler(
        job_defaults={
            'misfire_grace_time': 60,
            'coalesce': True,
        },
        executors={
            'default': {'type': 'threadpool', 'max_workers': 30}
        }
    )
    scheduler.add_listener(JobAction.my_listener, EVENT_JOB_ERROR | EVENT_JOB_MISSED | EVENT_JOB_EXECUTED)
    scheduler.start()


def _parse_interval(rate):
    """解析 interval 执行频率：秒 分 时（空格分隔，缺省为 0，至少一项大于 0）。"""
    parts = rate.split()
    if not 1 <= len(parts) <= 3:
        raise ValueError('interval 执行频率格式为「秒 分 时」，最多 3 项，例：30 或 0 5')
    try:
        values = [int(part) for part in parts]
    except ValueError:
        raise ValueError('interval 执行频率必须是整数，例：30 或 0 5') from None
    values += [0] * (3 - len(values))
    if any(value < 0 for value in values):
        raise ValueError('interval 执行频率不能为负数')
    if not any(values):
        raise ValueError('interval 执行频率不能全为 0')
    return {'seconds': values[0], 'minutes': values[1], 'hours': values[2]}


_CRON_RANGES = (
    ('秒', 0, 59), ('分', 0, 59), ('时', 0, 23),
    ('日', 1, 31), ('月', 1, 12), ('星期', 0, 6), ('年', 1970, 9999),
)

_DATE_RE = re.compile(
    r'^(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'(?:[ T](?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})'
    r'(?:\.(?P<microsecond>\d{1,6}))?(?P<tz>Z|[+-]\d\d:\d\d)?)?$'
)


def _check_cron_field(name, value, low, high):
    """校验 cron 单个字段：支持 *、数字、区间、步长及逗号列表。"""
    allow_name = name in ('月', '星期')
    for item in value.split(','):
        expr, _, step = item.partition('/')
        if not expr:
            raise ValueError('cron %s 存在空项：%s' % (name, value))
        if step and (not step.isdigit() or int(step) <= 0):
            raise ValueError('cron %s 步长必须是正整数：%s' % (name, item))
        if expr == '*':
            continue
        if any(char.isalpha() for char in expr):
            if allow_name:
                # jan、mon 之类的英文缩写交给 APScheduler 校验
                continue
            raise ValueError('cron %s 仅支持数字、*、区间和步长，当前为：%s' % (name, item))
        try:
            start, _, end = expr.partition('-')
            values = [int(start)] + ([int(end)] if end else [])
        except ValueError:
            raise ValueError('cron %s 仅支持数字、*、区间和步长，当前为：%s' % (name, item)) from None
        if any(not low <= number <= high for number in values):
            raise ValueError('cron %s 取值范围为 %s-%s，当前为：%s' % (name, low, high, item))
        if len(values) == 2 and values[0] > values[1]:
            raise ValueError('cron %s 区间起始值不能大于结束值：%s' % (name, item))


def _parse_cron(rate):
    """解析 cron 执行频率：秒 分 时 日 月 星期 年，共 7 项。"""
    parts = rate.split()
    if len(parts) != 7:
        raise ValueError('cron 执行频率格式为「秒 分 时 日 月 星期 年」，共 7 项，例：0 0 2 * * * *')
    for part, (name, low, high) in zip(parts, _CRON_RANGES):
        _check_cron_field(name, part, low, high)
    return {'second': parts[0], 'minute': parts[1], 'hour': parts[2], 'day': parts[3],
            'month': parts[4], 'day_of_week': parts[5], 'year': parts[6]}


def _parse_date(value):
    """校验 date 执行频率：2019-8-30 01:00:00，格式与 APScheduler 保持一致。"""
    text = value.strip() if isinstance(value, str) else ''
    if not text:
        raise ValueError('date 执行频率不能为空，例：2019-8-30 01:00:00')
    match = _DATE_RE.match(text)
    if not match:
        raise ValueError('date 执行频率格式应为 YYYY-MM-DD HH:MM:SS，例：2019-8-30 01:00:00')
    try:
        datetime(**{key: int(number) for key, number in match.groupdict().items()
                    if key != 'tz' and number})
    except ValueError:
        raise ValueError('date 执行频率不是有效的日期时间：%s' % text) from None
    return text


_JOB_RATE_PARSERS = {
    'date': _parse_date, 'cron': _parse_cron, 'interval': _parse_interval,
}


def parse_job_rate(action_type, rate):
    """按调度类型校验执行频率，非法时抛出 ValueError。"""
    parser = _JOB_RATE_PARSERS.get(action_type)
    if parser is not None:
        parser(rate)


class JobAction:
    @staticmethod
    def start_date_job(trigger, job_rate, id):
        exec(JobList.objects.get(id=id).trigger.func_path)
        trigger_id = trigger + '-' + id
        scheduler.add_job(eval(trigger), 'date', run_date=_parse_date(job_rate), id=trigger_id,
                          args=[trigger_id, id, 'date'], replace_existing=True)

    @staticmethod
    def start_cron_job(trigger, job_rate, id):
        exec(JobList.objects.get(id=id).trigger.func_path)
        trigger_id = trigger + '-' + id
        # 秒 分 时 日 月 星期 年
        scheduler.add_job(eval(trigger), 'cron', id=trigger_id, args=[trigger_id, id, 'cron'],
                          replace_existing=True, **_parse_cron(job_rate))

    @staticmethod
    def start_interval_job(trigger, job_rate, id):
        exec(JobList.objects.get(id=id).trigger.func_path)
        trigger_id = trigger + '-' + id
        scheduler.add_job(eval(trigger), 'interval', id=trigger_id, args=[trigger_id, id, 'interval'],
                          replace_existing=True, **_parse_interval(job_rate))

    @staticmethod
    def run_job(trigger, id):
        exec(JobList.objects.get(id=id).trigger.func_path)
        trigger_id = trigger + '-' + id
        scheduler.add_job(eval(trigger), 'date', run_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          id=trigger_id, args=[trigger_id, id, 'now'])

    # 停止任务
    @staticmethod
    def stop_job(trigger_id):
        if not scheduler.get_job(trigger_id):
            return False
        scheduler.remove_job(trigger_id)
        return True

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
        if not scheduler.get_job(trigger_id):
            return False
        if job_value[0] == 'cron':
            scheduler.reschedule_job(trigger_id, trigger='cron', **_parse_cron(job_value[1]))
            return True
        if job_value[0] == 'date':
            scheduler.reschedule_job(trigger_id, trigger='date', run_date=_parse_date(job_value[1]))
            return True
        if job_value[0] == 'interval':
            scheduler.reschedule_job(trigger_id, trigger='interval', **_parse_interval(job_value[1]))
            return True
        return False

    @staticmethod
    def get_jobs():
        jobs = [item.id for item in scheduler.get_jobs()]
        logger.info(str(os.getpid()) + ' - all jobs：' + str(jobs))

    @staticmethod
    def my_listener(event):
        if event.exception:
            job = scheduler.get_job(event.job_id)
            logger.error("jobname=%s|jobtrigger=%s|errcode=%s|exception=[%s]|traceback=[%s]|scheduled_time=%s",
                         job.name, job.trigger, event.code, event.exception, event.traceback, event.scheduled_run_time)
