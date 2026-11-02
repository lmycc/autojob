from django.db import migrations


TEST_FUNC_PATH = 'from autojob.test_job import test'
TEST_JOB_NAME = '内置测试定时任务'


def add_builtin_test_job(apps, schema_editor):
    JobTrigger = apps.get_model('autojob', 'JobTrigger')
    JobList = apps.get_model('autojob', 'JobList')

    trigger, _ = JobTrigger.objects.get_or_create(
        func_path=TEST_FUNC_PATH,
        defaults={
            'trigger_name': '测试触发器',
            'trigger_func': 'test',
            'description': 'autojob 内置测试定时任务',
        },
    )
    JobList.objects.get_or_create(
        job_name=TEST_JOB_NAME,
        trigger=trigger,
        defaults={
            'action_type': 'cron',
            'job_state': 1,
            'job_rate': '0 * * * * * *',
            'time': 0,
        },
    )


def remove_builtin_test_job(apps, schema_editor):
    JobTrigger = apps.get_model('autojob', 'JobTrigger')
    JobList = apps.get_model('autojob', 'JobList')

    JobList.objects.filter(
        job_name=TEST_JOB_NAME,
        trigger__func_path=TEST_FUNC_PATH,
    ).delete()
    JobTrigger.objects.filter(
        func_path=TEST_FUNC_PATH,
        joblist__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('autojob', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_builtin_test_job, remove_builtin_test_job),
    ]
