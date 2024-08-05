from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from django.contrib import admin
from django.core.cache import cache
from django.utils import timezone

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
    list_display = ('id', 'job_name', 'job_state', 'action_type', 'job_rate', 'update_time')
    list_display_links = ('id', 'job_name')
    list_filter = ('job_state',)
    list_editable = ('action_type', 'job_rate',)
    list_per_page = 20
    list_max_show_all = 7
    ordering = ('-job_state', 'id',)
    actions = ['start_job', 'stop_job']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            readonly_fields = ('trigger_id', 'job_state', 'update_time',)
        else:
            readonly_fields = ('job_state',)
        return readonly_fields

    def save_model(self, request, obj, form, change):
        if obj.job_state == 1:
            cache.set('modify_' + obj.trigger.trigger_func + '-' + str(obj.id), (obj.action_type, obj.job_rate),
                      timeout=60)
        obj.save()

    def start_job(self, request, queryset):
        global job_name
        trigger_list = queryset.values('trigger_id')
        rate_list = queryset.values('job_rate')
        id_list = queryset.values('id')
        job_num = len(id_list)
        name_list = queryset.values('job_name')
        action_type = queryset.values('action_type')
        update_time = queryset.values('update_time')
        current_time = timezone.now()
        for (trigger, rate, id_, name, type_, time_) in zip(trigger_list, rate_list, id_list, name_list, action_type,
                                                            update_time):
            try:
                job_name = name.get('job_name')
                job_rate = rate.get('job_rate')
                job_id = id_.get('id')
                trigger_name = JobList.objects.get(id=job_id).trigger.trigger_func
                job_type = type_.get('action_type')
                last_time = time_.get('update_time')
                interval_time = current_time - last_time
                seconds = interval_time.days * 24 * 3600 + interval_time.seconds
                if seconds < 60:
                    messages.warning(request, '请于 %ss 后在启动 %s' % (str(60 - seconds), job_name))
                    job_num -= 1
                    continue
                if hasattr(JobAction(), 'start_%s_job' % job_type):
                    func = getattr(JobAction(), 'start_%s_job' % job_type)
                    func(trigger_name, job_rate, str(job_id))
                    queryset.filter(id=job_id).update(job_state=1, update_time=current_time)
                else:
                    messages.error(request, '【启动错误】 ' + job_name + ' 任务不存在!')
                    job_num -= 1
            except ConflictingIdError as e:
                logger.error(e)
                messages.error(request, job_name + ' 任务启动发生冲突！')
                job_num -= 1
            except Exception as e:
                logger.error(e)
                messages.error(request, job_name + ' 任务启动异常！<br/>请检查调度类型或执行频率')
                job_num -= 1
        JobAction().get_jobs()
        if job_num > 0 and len(id_list) > 1:
            messages.success(request,
                             ('其余' if job_num != len(id_list) else '所选') + ' %s 个任务启动成功' % str(job_num))
        elif job_num == len(id_list) == 1:
            messages.success(request, '%s 任务启动成功' % job_name)
        return messages

    start_job.short_description = '启动任务'
    start_job.icon = 'el-icon-video-play'
    start_job.type = 'success'

    def stop_job(self, request, queryset):
        global job_name
        name_list = queryset.values('job_name')
        trigger_list = queryset.values('trigger')
        id_list = queryset.values('id')
        job_num = len(id_list)
        current_time = timezone.now()
        for (trigger, id_, name) in zip(trigger_list, id_list, name_list):
            try:
                job_name = name.get('job_name')
                job_id = id_.get('id')
                trigger_name = JobList.objects.get(id=job_id).trigger.trigger_func
                JobAction.stop_job(trigger_name + '-' + str(job_id))
                queryset.filter(id=job_id).update(job_state=0, update_time=current_time)
                cache.set('stop_' + str(job_id), trigger_name + '-' + str(job_id), timeout=60)
            except JobLookupError as e:
                logger.error(e)
                job_num -= 1
                messages.error(request, job_name + " 任务不存在！")
            except Exception as e:
                logger.error(e)
                job_num -= 1
                messages.error(request, job_name + ' 任务停止异常！')
        JobAction().get_jobs()
        if job_num > 0 and len(id_list) > 1:
            messages.success(request,
                             ('其余' if job_num != len(id_list) else '所选') + ' %s 个任务已停止' % str(job_num))
        elif job_num == len(id_list) == 1:
            messages.success(request, "%s 任务已停止" % job_name)
        return messages

    stop_job.short_description = '停止任务'
    stop_job.icon = 'el-icon-video-pause'
    stop_job.type = 'danger'
