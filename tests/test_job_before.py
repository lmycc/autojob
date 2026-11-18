# coding=utf-8
"""job_before 装饰器的执行条件测试。"""
from unittest.mock import patch

from django.test import TestCase

from autojob.job_new import JobAction
from autojob.job_tool import job_before
from autojob.models import JobList, JobTrigger


class JobBeforeTests(TestCase):
    def setUp(self):
        self.trigger = JobTrigger.objects.create(
            trigger_name='demo', trigger_func='demo',
            func_path='tests.job_before_demo', description='测试任务',
        )
        self.job = JobList.objects.create(
            job_name='demo', trigger=self.trigger,
            action_type='cron', job_rate='0 * * * * * *', job_state=1,
        )
        self.calls = []

    def _get_job(self):
        self.job.refresh_from_db()

    def _make_job(self, action_type='cron', job_state=1):
        self.job.action_type = action_type
        self.job.job_state = job_state
        self.job.save()

    def _run(self, lock_ok=True, action_type='cron', job_state=1):
        def func(*args, **kwargs):
            self.calls.append(args)

        decorated = job_before(func)
        job_id = 'demo-%s' % self.job.id
        with patch('autojob.job_tool.get_lock', return_value=lock_ok), \
                patch.object(JobAction, 'stop_job') as stop_job:
            if action_type == 'now':
                decorated(job_id, str(self.job.id), 'now')
            else:
                decorated(job_id, str(self.job.id), action_type)
        return stop_job

    def test_now_skips_all_checks(self):
        self._make_job(job_state=0)
        stop_job = self._run(action_type='now')
        self.assertEqual(len(self.calls), 1)
        stop_job.assert_not_called()
        self._get_job()
        self.assertEqual(self.job.job_state, 0)

    def test_stopped_job_removed_from_scheduler(self):
        self._make_job(job_state=0)
        stop_job = self._run(action_type='cron')
        self.assertEqual(self.calls, [])
        stop_job.assert_called_once()

    def test_lock_failed_removed_from_scheduler(self):
        stop_job = self._run(lock_ok=False)
        self.assertEqual(self.calls, [])
        stop_job.assert_called_once()

    def test_cron_runs_and_keeps_state(self):
        stop_job = self._run(action_type='cron')
        self.assertEqual(len(self.calls), 1)
        stop_job.assert_not_called()
        self._get_job()
        self.assertEqual(self.job.job_state, 1)

    def test_date_runs_and_marks_stopped(self):
        self._make_job(action_type='date')
        self._run(action_type='date')
        self.assertEqual(len(self.calls), 1)
        self._get_job()
        self.assertEqual(self.job.job_state, 0)
