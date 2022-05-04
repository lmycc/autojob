from django.db import models


class job_list(models.Model):
    decpet = models.CharField('描述', max_length=255)
    job_name = models.CharField('任务名称', max_length=25)
    trigger_name = models.CharField('触发器', max_length=25)
    type_choices = (('date', 'date'), ('cron', 'cron'))
    type_content = '''调度类型 对应 参数（执行频率）  例：<br/>
                    1、date：2019年8月30日 凌晨一点 执行任务<br/>参数值：2019-8-30 01:00:00 <br/>
                    2、cron：每天 凌晨两点 执行任务 (秒 分 时 日 月 星期 年)<br/>参数值：0 0 2 * * * *'''
    action_type = models.CharField('调度类型', choices=type_choices, max_length=25, default='cron')
    gender_choices = ((0, '停止'), (1, '启动'),)
    job_state = models.IntegerField('任务状态', choices=gender_choices, default=0)
    job_rate = models.CharField('执行频率', help_text=type_content, max_length=50)
    time = models.IntegerField('执行次数', default=0)

    def __str__(self):
        return self.decpet

    class Meta:
        verbose_name_plural = '定时任务'
