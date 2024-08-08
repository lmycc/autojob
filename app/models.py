from django.db import models
from django.utils import timezone


class JobTrigger(models.Model):
    trigger_name = models.CharField('触发器名称', max_length=25)
    trigger_func = models.CharField('触发器', max_length=25)
    func_desc = '例：from app.test_job import test'
    func_path = models.CharField('触发器路径', help_text=func_desc, max_length=255)
    description = models.CharField('描述', max_length=50)

    def __str__(self):
        return self.trigger_name

    class Meta:
        verbose_name = '定时任务触发器'
        verbose_name_plural = verbose_name


class JobList(models.Model):
    job_name = models.CharField('任务名称', max_length=25)
    trigger = models.ForeignKey(JobTrigger, on_delete=models.SET_NULL, null=True)
    type_choices = (('date', 'date'), ('cron', 'cron'))
    type_content = '''调度类型 对应 参数（执行频率）  例：<br/>
                        1、date：2019年8月30日 凌晨一点 执行任务<br/>参数值：2019-8-30 01:00:00 <br/>
                        2、cron：每天 凌晨两点 执行任务 (秒 分 时 日 月 星期 年)<br/>参数值：0 0 2 * * * *'''
    action_type = models.CharField('调度类型', choices=type_choices, max_length=25, default='cron')
    gender_choices = ((0, '停止'), (1, '启动'),)
    job_state = models.IntegerField('任务状态', choices=gender_choices, default=0)
    job_rate = models.CharField('执行频率', help_text=type_content, max_length=50)
    time = models.IntegerField('执行次数', default=0)
    help_text_update_time = '''任务状态变更才会更新时间<br/>
                                启动任务 当前时间须比上次变更时间大于一分钟<br/>
                                停止任务 无需等待'''
    update_time = models.DateTimeField('更新时间', auto_now_add=timezone.now(), help_text=help_text_update_time)

    def __str__(self):
        return self.job_name

    class Meta:
        verbose_name_plural = '定时任务'
