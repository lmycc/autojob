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
                    return messages.error(request, '?????????????????? ' + job_name + ' ???????????????!')
            except ConflictingIdError as e:
                logger.error(e)
                return messages.error(request, job_name + ' ???????????????????????????')
            except Exception as e:
                logger.error(e)
                return messages.error(request, job_name + ' ?????????????????????<br/>????????????????????????????????????')
        return messages.success(request, (job_name if len(id_list) == 1 else '??????') + " ??????????????????")

    start_job.short_description = '????????????'
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
            return messages.success(request, (name_list[0].get('job_name') if len(name_list) == 1 else '??????') + " ???????????????")
        except JobLookupError as e:
            logger.error(e)
            return messages.error(request, job_name + " ??????????????????")

    stop_job.short_description = '????????????'
    stop_job.type = 'danger'
    actions = ['start_job', 'stop_job']
