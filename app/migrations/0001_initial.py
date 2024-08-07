# Generated by Django 3.2.25 on 2024-08-05 09:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='JobTrigger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trigger_name', models.CharField(max_length=25, verbose_name='trigger_name')),
                ('trigger_func', models.CharField(max_length=25, verbose_name='trigger_func')),
                ('func_path', models.CharField(help_text='e.p.：from autojob.job_test import job_test', max_length=255, verbose_name='func_path')),
                ('description', models.CharField(max_length=50, verbose_name='description')),
            ],
            options={
                'verbose_name_plural': '定时任务触发器',
                'index_together': {('trigger_func', 'func_path')},
            },
        ),
        migrations.CreateModel(
            name='JobList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_name', models.CharField(max_length=25, verbose_name='job_name')),
                ('action_type', models.CharField(choices=[('date', 'date'), ('cron', 'cron')], default='cron', max_length=25, verbose_name='scheduling type')),
                ('job_state', models.IntegerField(choices=[(0, 'stop'), (1, 'start')], default=0, verbose_name='job status')),
                ('job_rate', models.CharField(help_text='Parameter corresponding to scheduling type (execution frequency) ：<br/>\n        1、date：Execute task at 1am on August 30, 2019<br/>value：2019-8-30 01:00:00 <br/>\n        2、cron：Execute tasks at 2:00 am every day(second minute hour day month week year (The parameters must \n        be in this order))<br/>value：0 0 2 * * * *', max_length=50, verbose_name='frequency')),
                ('time', models.IntegerField(default=0, verbose_name='number of times')),
                ('update_time', models.DateTimeField(auto_now_add=True, help_text='The task status change before the time is updated<br/>\n                    start job: The current time must be greater than one minute from the last time it was changed<br/>\n                    stop job: No need to wait to restart', verbose_name='update time')),
                ('trigger', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='autojob.jobtrigger')),
            ],
            options={
                'verbose_name_plural': '定时任务',
            },
        ),
    ]
