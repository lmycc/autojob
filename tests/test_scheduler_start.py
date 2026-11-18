# coding=utf-8
"""调度器启动幂等性测试。"""
from unittest.mock import patch

from django.test import SimpleTestCase

from autojob import job_new


class FakeScheduler:
    instances = []

    def __init__(self, **kwargs):
        self.running = False
        FakeScheduler.instances.append(self)

    def add_listener(self, *args, **kwargs):
        pass

    def start(self):
        self.running = True


class StartSchedulerTests(SimpleTestCase):
    def setUp(self):
        FakeScheduler.instances = []
        patcher = patch.object(job_new, 'BackgroundScheduler', FakeScheduler)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(job_new.__dict__.pop, 'scheduler', None)

    def test_second_call_returns_false(self):
        self.assertTrue(job_new.start_scheduler())
        self.assertFalse(job_new.start_scheduler())
        self.assertEqual(len(FakeScheduler.instances), 1)
        self.assertTrue(job_new.scheduler.running)
