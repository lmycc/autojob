# coding=utf-8
"""执行频率参数校验的单元测试。"""
from django.test import SimpleTestCase

from autojob.job_new import _parse_cron, _parse_date, _parse_interval, parse_job_rate


class IntervalParseTests(SimpleTestCase):
    def test_valid(self):
        self.assertEqual(
            _parse_interval('30'), {'seconds': 30, 'minutes': 0, 'hours': 0}
        )
        self.assertEqual(
            _parse_interval('0 5'), {'seconds': 0, 'minutes': 5, 'hours': 0}
        )
        self.assertEqual(
            _parse_interval('1 2 3'), {'seconds': 1, 'minutes': 2, 'hours': 3}
        )

    def test_invalid(self):
        for rate in ('', '0 0 0', '-1', 'a 1', '1 2 3 4'):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    _parse_interval(rate)


class CronParseTests(SimpleTestCase):
    def test_valid(self):
        for rate in (
                '0 0 2 * * * *',
                '*/5 * * * * * *',
                '0,30 * * * * * *',
                '0 0 9-17 * * 1-5 *',
                '0 0 0 * jan mon *',
        ):
            with self.subTest(rate=rate):
                self.assertEqual(len(_parse_cron(rate)), 7)

    def test_invalid(self):
        for rate in (
                '0 0 2 * * *',  # 少一项
                '0 0 2 * * * * *',  # 多一项
                '60 * * * * * *',  # 秒越界
                '0 0 25 * * * *',  # 时越界
                '0 */0 * * * * *',  # 步长为 0
                '0 0 0 0 * * *',  # 日越界
                '0 0 0 * 13 * *',  # 月越界
                '0 0 0 * * 7 *',  # 星期越界
                '0 0 0 * * * 1969',  # 年越界
                '0 0 5-3 * * * *',  # 区间倒序
                '0 0 a * * * *',  # 非法字符
                '0, * * * * * *',  # 空项
        ):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    _parse_cron(rate)


class DateParseTests(SimpleTestCase):
    def test_valid(self):
        for rate in (
                '2030-8-30 01:00:00',
                '2030-08-30T01:00:00',
                '2030-08-30',
                '2030-08-30 01:00:00.123456+08:00',
                ' 2030-8-30 01:00:00 ',
        ):
            with self.subTest(rate=rate):
                self.assertEqual(_parse_date(rate), rate.strip())

    def test_invalid(self):
        for rate in ('', '2030/8/30', '2030-2-30', '2030-13-30', '2030-8-30 25:00:00'):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    _parse_date(rate)


class ParseJobRateTests(SimpleTestCase):
    def test_dispatch(self):
        parse_job_rate('interval', '30')
        parse_job_rate('cron', '0 0 2 * * * *')
        parse_job_rate('date', '2030-8-30 01:00:00')
        # 未知类型不做校验，由调度器自行决定
        parse_job_rate('unknown', 'whatever')

    def test_invalid_propagates(self):
        for action_type, rate in (
                ('interval', '0 0 0'),
                ('cron', '0 0 25 * * * *'),
                ('date', '2030-2-30'),
        ):
            with self.subTest(action_type=action_type):
                with self.assertRaises(ValueError):
                    parse_job_rate(action_type, rate)
