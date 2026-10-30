# coding=utf-8
"""定时任务指令广播：把 Admin 的操作实时同步到每个 worker 进程。

为什么是线程而不是进程：
    APScheduler 实例保存在各个 worker 进程自己的内存里，
    子进程无法操作父进程的调度器，所以只能在每个进程内各起一个线程。

为什么用 Pub/Sub 而不是轮询 Redis key：
    发布方 publish 一次，所有订阅者立刻收到，延迟从"最长 60 秒"降到毫秒级，
    也不再需要每个 worker 每分钟全量扫描一遍 key。
"""
import json
import logging
import os
import threading
import time

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

# 进程内守卫：同一个进程只允许起一个监听线程
_started_pid = None
_guard = threading.Lock()
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.JOB_CMD_REDIS_URL)
    return _client


def publish_cmd(op, job_id, value=None):
    """发布一条任务指令，所有 worker 都会收到。

    op: 'stop' | 'modify'
    job_id: 调度器里的任务 id，格式为 ``{trigger_func}-{JobList.id}``
    value: modify 时为新值 (action_type, job_rate)
    """
    payload = {'op': op, 'job_id': job_id}
    if value is not None:
        payload['value'] = value
    try:
        receivers = _get_client().publish(settings.JOB_CMD_CHANNEL, json.dumps(payload))
    except redis.RedisError:
        # 发布失败不影响 Admin 操作本身：DB 状态已是准绳，
        # 停止指令会在任务下次触发时由 job_before 里的 job_state 检查兜底
        logger.exception('指令发布失败，已降级为数据库状态兜底: %s', payload)
        return 0
    logger.info('已发布指令 %s，在线订阅者 %s 个', payload, receivers)
    return receivers


def start_listener():
    """在当前进程内启动指令监听线程（幂等）。"""
    global _started_pid
    pid = os.getpid()
    with _guard:
        if _started_pid == pid:
            return False
        _started_pid = pid
    thread = threading.Thread(
        target=_listen_forever, name='autojob-cmd-%s' % pid, daemon=True
    )
    thread.start()
    logger.info('任务指令监听线程已启动, pid=%s', pid)
    return True


def _listen_forever():
    """订阅循环，断线后自动重连。"""
    pubsub = None
    while True:
        try:
            if pubsub is None:
                client = redis.Redis.from_url(
                    settings.JOB_CMD_REDIS_URL, health_check_interval=30
                )
                pubsub = client.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(settings.JOB_CMD_CHANNEL)
                logger.info(
                    '已订阅 %s, pid=%s', settings.JOB_CMD_CHANNEL, os.getpid()
                )
            message = pubsub.get_message(timeout=5)
            if message is None:
                continue
            _handle(json.loads(message['data']))
        except Exception:
            logger.exception('任务指令监听中断，3 秒后重连')
            if pubsub is not None:
                try:
                    pubsub.close()
                except Exception:
                    pass
                pubsub = None
            time.sleep(3)


def _handle(payload):
    from app.job_new import JobAction
    from apscheduler.jobstores.base import JobLookupError

    op = payload.get('op')
    job_id = payload.get('job_id')
    if not job_id:
        return
    try:
        if op == 'stop':
            JobAction.stop_job(job_id)
            logger.info('收到停止指令: %s, pid=%s', job_id, os.getpid())
        elif op == 'modify':
            JobAction.modify_job(job_id, payload.get('value'))
            logger.info('收到修改指令: %s -> %s, pid=%s', job_id, payload.get('value'), os.getpid())
        else:
            logger.warning('收到未知指令: %s', payload)
    except JobLookupError:
        # 目标任务在本进程的调度器里根本不存在（还没启动 / 已被其他 worker 停掉）
        # 这种情况不应该让 pubsub 连接炸掉
        logger.warning('指令 %s 未执行，本进程没有这个任务: %s, pid=%s', op, job_id, os.getpid())
    except Exception:
        logger.exception('处理指令失败: %s', payload)
