# coding=utf-8
import datetime
import logging

from app.job_tool import job_before

logger = logging.getLogger(__name__)


@job_before
def test(*args):
    # 此处就是你需要执行的任务
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(now + '__这是一个测试的定时任务:' + args[0])
