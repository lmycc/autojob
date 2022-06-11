from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from django.contrib import admin

from app.job_new import JobAction

from .models import JobList, JobListTrigger
import logging
from django.contrib import messages

logger = logging.getLogger(__name__)


# Register your models here.
@admin.register(JobListTrigger)
class JobListTriggerAdmin(admin.ModelAdmin):
    list_display = ('id', 'trigger_name', 'trigger_func', 'func_path', 'description')
    list_display_links = ('id', 'trigger_name')
    list_per_page = 20
    list_max_show_all = 7
    ordering = ('id',)


# Register your models here.
@admin.register(JobList)
class JobListAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_name', 'job_state', 'action_type', 'job_rate')
    list_display_links = ('id', 'job_name')
    list_filter = ('job_state',)
    list_editable = ('action_type', 'job_rate',)
    list_per_page = 20
    list_max_show_all = 7
    ordering = ('-job_state', 'id',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('trigger_id', 'job_state')
        return ('job_state',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            readonly_fields = ('job_state', 'trigger_name',)
        else:
            readonly_fields = ('job_state',)
        return readonly_fields

    def save_model(self, request, obj, form, change):
        from django.core.cache import cache
        if obj.job_state == 1:
            cache.set(obj.trigger.trigger_func + '-' + str(obj.id), (obj.action_type, obj.job_rate))
        obj.save()

    def start_job(self, request, queryset):
        global job_name
        trigger_list = queryset.values('trigger_id')
        rate_list = queryset.values('job_rate')
        id_list = queryset.values('id')
        name_list = queryset.values('job_name')
        action_type = queryset.values('action_type')
        for (trigger, rate, id, name, type) in zip(trigger_list, rate_list, id_list, name_list, action_type):
            try:
                job_rate = rate.get('job_rate')
                job_id = id.get('id')
                trigger_name = JobList.objects.get(id=job_id).trigger.trigger_func
                print(trigger_name)
                job_name = name.get('job_name')
                job_type = type.get('action_type')
                if hasattr(JobAction(), 'start_%s_job' % job_type):
                    func = getattr(JobAction(), 'start_%s_job' % job_type)
                    func(trigger_name, job_rate, str(job_id))
                    queryset.update(job_state=1)
                else:
                    return messages.error(request, '【启动错误】 ' + job_name + ' 任务不存在!')
            except ConflictingIdError as e:
                logger.error(e)
                return messages.error(request, job_name + ' 任务启动发生冲突！')
            except Exception as e:
                logger.error(e)
                return messages.error(request, job_name + ' 任务启动异常！<br/>请检查调度类型或执行频率')
        return messages.success(request, (job_name if len(id_list) == 1 else '所选') + " 任务启动成功")

    start_job.short_description = '启动任务'
    start_job.type = 'success'

    def stop_job(self, request, queryset):
        global job_name
        name_list = queryset.values('job_name')
        trigger_list = queryset.values('trigger')
        id_list = queryset.values('id')
        try:
            for (trigger, id, name) in zip(trigger_list, id_list, name_list):
                job_id = id.get('id')
                trigger_name = JobList.objects.get(id=job_id).trigger.trigger_func
                job_name = name.get('job_name')
                JobAction.stop_job(trigger_name + '-' + str(job_id))
                queryset.update(job_state=0)
            return messages.success(request, (name_list[0].get('job_name') if len(name_list) == 1 else '所选') + " 任务已停止")
        except JobLookupError as e:
            logger.error(e)
            return messages.error(request, job_name + " 任务不存在！")

    stop_job.short_description = '停止任务'
    stop_job.type = 'danger'
    actions = ['start_job', 'stop_job']
