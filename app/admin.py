from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from django.contrib import admin

from app.job_new import JobAction

from .models import job_list
import logging
from django.contrib import messages

logger = logging.getLogger(__name__)


# Register your models here.
@admin.register(job_list)
class JOBLISTAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_name', 'decpet', 'trigger_name', 'job_state', 'action_type', 'job_rate')
    list_display_links = ('id', 'job_name')
    list_filter = ('job_state',)
    list_editable = ('action_type', 'job_rate',)
    list_per_page = 20
    list_max_show_all = 7
    ordering = ('-job_state', 'id',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            readonly_fields = ('job_state', 'trigger_name',)
        else:
            readonly_fields = ('job_state',)
        return readonly_fields

    def save_model(self, request, obj, form, change):
        from django.core.cache import cache
        if obj.job_state == 1:
            cache.set(obj.trigger_name + '-' + str(obj.id), (obj.action_type, obj.job_rate))
        obj.save()

    def start_job(self, request, queryset):
        global job_name
        trigger_list = queryset.values('trigger_name')
        rate_list = queryset.values('job_rate')
        id_list = queryset.values('id')
        name_list = queryset.values('job_name')
        action_type = queryset.values('action_type')
        for (trigger, rate, id, name, type) in zip(trigger_list, rate_list, id_list, name_list, action_type):
            try:
                trigger_name = trigger.get('trigger_name')
                job_rate = rate.get('job_rate')
                job_id = id.get('id')
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
        trigger_list = queryset.values('trigger_name')
        id_list = queryset.values('id')
        try:
            for (trigger, id, name) in zip(trigger_list, id_list, name_list):
                trigger_name = trigger.get('trigger_name')
                job_id = id.get('id')
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
