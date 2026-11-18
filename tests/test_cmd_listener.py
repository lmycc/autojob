# coding=utf-8
"""指令广播去重与发布逻辑的单元测试。"""
import json
import logging
from unittest.mock import patch

import redis
from django.test import SimpleTestCase, override_settings

from autojob import cmd_listener

FAKE_CHANNEL = 'autojob:test'


class FakeRedis:
    """只实现指令模块用到的 set / publish。"""

    def __init__(self):
        self.claims = set()
        self.set_kwargs = None
        self.published = []
        self.publish_error = False

    def set(self, key, value, nx=False, ex=None):
        self.set_kwargs = {'key': key, 'value': value, 'nx': nx, 'ex': ex}
        if key in self.claims:
            return None
        self.claims.add(key)
        return True

    def publish(self, channel, data):
        if self.publish_error:
            raise redis.RedisError('redis down')
        self.published.append((channel, data))
        return 2


@override_settings(JOB_CMD_CHANNEL=FAKE_CHANNEL)
class ClaimCmdLogTests(SimpleTestCase):
    def setUp(self):
        self.client = FakeRedis()
        patcher = patch.object(cmd_listener, '_get_client', return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_same_cmd_only_claimed_once(self):
        self.assertTrue(cmd_listener._claim_cmd_log('cmd-1'))
        self.assertFalse(cmd_listener._claim_cmd_log('cmd-1'))
        self.assertTrue(cmd_listener._claim_cmd_log('cmd-2'))

    def test_claim_key_and_ttl(self):
        cmd_listener._claim_cmd_log('cmd-3')
        kwargs = self.client.set_kwargs
        self.assertEqual(kwargs['key'], '%s:executed:cmd-3' % FAKE_CHANNEL)
        self.assertTrue(kwargs['nx'])
        self.assertEqual(kwargs['ex'], 10)

    def test_empty_cmd_always_allowed(self):
        self.assertTrue(cmd_listener._claim_cmd_log(None))
        self.assertIsNone(self.client.set_kwargs)


@override_settings(JOB_CMD_CHANNEL=FAKE_CHANNEL)
class PublishCmdTests(SimpleTestCase):
    def setUp(self):
        self.client = FakeRedis()
        patcher = patch.object(cmd_listener, '_get_client', return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_payload_contents(self):
        cmd_listener.publish_cmd('stop', 'demo-1')
        channel, data = self.client.published[0]
        self.assertEqual(channel, FAKE_CHANNEL)
        payload = json.loads(data)
        self.assertEqual(payload['op'], 'stop')
        self.assertEqual(payload['job_id'], 'demo-1')
        self.assertTrue(payload['cmd_id'])
        self.assertNotIn('value', payload)

    def test_modify_payload_contains_value(self):
        cmd_listener.publish_cmd('modify', 'demo-1', ('cron', '0 0 3 * * * *'))
        payload = json.loads(self.client.published[0][1])
        self.assertEqual(payload['value'], ['cron', '0 0 3 * * * *'])

    def test_publish_failure_returns_zero(self):
        self.client.publish_error = True
        with self.assertLogs('autojob.cmd_listener', level='ERROR') as logs:
            receivers = cmd_listener.publish_cmd('stop', 'demo-1')
        self.assertEqual(receivers, 0)
        self.assertIn('指令发布失败', logs.output[0])

    def test_publish_log_precedes_publish(self):
        """发布日志必须早于 publish 调用，避免接收日志先于发布日志。"""
        events = []

        class Recorder(logging.Handler):
            def emit(self, record):
                events.append(record.getMessage())

        handler = Recorder()
        old_level = cmd_listener.logger.level
        cmd_listener.logger.setLevel(logging.INFO)
        cmd_listener.logger.addHandler(handler)
        self.addCleanup(cmd_listener.logger.setLevel, old_level)
        self.addCleanup(cmd_listener.logger.removeHandler, handler)

        def fake_publish(channel, data):
            events.append('__publish__')
            return 2

        self.client.publish = fake_publish
        cmd_listener.publish_cmd('stop', 'demo-1')
        self.assertTrue(events[0].startswith('发布 stop 指令'), events)
        self.assertEqual(events[1], '__publish__')
