import os

from apscheduler.jobstores.base import ConflictingIdError
from django import forms
from django.contrib import admin
from django.utils import timezone

from autojob.cmd_listener import publish_cmd
from autojob.job_new import JobAction, load_job_func, parse_job_rate

from .models import JobList, JobTrigger
import logging
from django.contrib import messages

logger = logging.getLogger(__name__)


class JobListForm(forms.ModelForm):
    """保存任务时校验执行频率，规则复用 job_new。"""

    class Meta:
        model = JobList
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        action_type = cleaned_data.get('action_type')
        job_rate = cleaned_data.get('job_rate')
        if action_type and job_rate:
            try:
                parse_job_rate(action_type, job_rate)
            except ValueError as exc:
                self.add_error('job_rate', str(exc))
        return cleaned_data


class JobTriggerForm(forms.ModelForm):
    """保存触发器时校验触发器路径可解析、可导入。"""

    class Meta:
        model = JobTrigger
        fields = '__all__'

    def clean_func_path(self):
        func_path = self.cleaned_data.get('func_path', '').strip()
        try:
            load_job_func(func_path)
        except ValueError as exc:
            raise forms.ValidationError(str(exc))
        return func_path


# Register your models here.
@admin.register(JobTrigger)
class JobTriggerAdmin(admin.ModelAdmin):
    form = JobTriggerForm
    list_display = ('id', 'trigger_name', 'trigger_func', 'func_path', 'description')
    list_display_links = ('id', 'trigger_name')
    list_per_page = 20
    list_max_show_all = 7
    ordering = ('id',)


# Register your models here.
@admin.register(JobList)
class JobListAdmin(admin.ModelAdmin):
    form = JobListForm
    list_display = ('id', 'job_name', 'job_state', 'action_type', 'job_rate', 'update_time')
    list_display_links = ('id', 'job_name')
    list_filter = ('job_state',)
    list_editable = ('action_type', 'job_rate',)
    list_per_page = 20
    list_max_show_all = 7
    ordering = ('-job_state', 'id',)
    actions = ['start_job', 'stop_job', 'action_job']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            readonly_fields = ('trigger_id', 'job_state', 'update_time',)
        else:
            readonly_fields = ('job_state',)
        return readonly_fields

    def get_changelist_form(self, request, **kwargs):
        # 列表页的 action_type / job_rate 内联编辑同样要走执行频率校验
        kwargs.setdefault('form', JobListForm)
        return super().get_changelist_form(request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.job_state == 1 and obj.trigger_id:
            # 保存成功后再广播给所有 worker，避免保存失败时已发出指令
            publish_cmd('modify', obj.trigger.trigger_func + '-' + str(obj.id),
                        (obj.action_type, obj.job_rate))

    def start_job(self, request, queryset):
        global job_name
        trigger_list = queryset.values('trigger_id')
        rate_list = queryset.values('job_rate')
        id_list = queryset.values('id')
        job_num = len(id_list)
        name_list = queryset.values('job_name')
        action_type = queryset.values('action_type')
        current_time = timezone.now()
        for (trigger, rate, id_, name, type_) in zip(trigger_list, rate_list, id_list, name_list, action_type):
            try:
                job_name = name.get('job_name')
                job_rate = rate.get('job_rate')
                job_id = id_.get('id')
                trigger_name = JobList.objects.get(id=job_id).trigger.trigger_func
                job_type = type_.get('action_type')
                if hasattr(JobAction, 'start_%s_job' % job_type):
                    logger.info('发布 %s 指令 %s', 'start', {'op': 'start', 'job_id': job_id})
                    func = getattr(JobAction, 'start_%s_job' % job_type)
                    func(trigger_name, job_rate, str(job_id))
                    queryset.filter(id=job_id).update(job_state=1, update_time=current_time)
                    logger.info('%s 指令执行完成: %s, worker_pid=%s', 'start', job_id, os.getpid())
                else:
                    messages.error(request, '【启动错误】 ' + job_name + ' 任务不存在!')
                    job_num -= 1
            except ConflictingIdError as e:
                logger.exception('任务启动冲突: %s', e)
                messages.error(request, job_name + ' 任务启动发生冲突！')
                job_num -= 1
            except Exception as e:
                logger.exception('任务启动异常: %s', e)
                messages.error(request, job_name + ' 任务启动异常！<br/>请检查调度类型或执行频率')
                job_num -= 1
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
                queryset.filter(id=job_id).update(job_state=0, update_time=current_time)
                # 广播给所有 worker，立即从各自的调度器移除
                publish_cmd('stop', trigger_name + '-' + str(job_id))
            except Exception as e:
                logger.exception('任务停止异常: %s', e)
                job_num -= 1
                messages.error(request, job_name + ' 任务停止异常！')
        if job_num > 0 and len(id_list) > 1:
            messages.success(request,
                             ('其余' if job_num != len(id_list) else '所选') + ' %s 个任务已停止' % str(job_num))
        elif job_num == len(id_list) == 1:
            messages.success(request, "%s 任务已停止" % job_name)
        return messages

    stop_job.short_description = '停止任务'
    stop_job.icon = 'el-icon-video-pause'
    stop_job.type = 'danger'

    def action_job(self, request, queryset):
        global job_name
        job_num = len(queryset.values('id'))
        if job_num > 1:
            messages.error(request, "最多只能选择一个任务立即执行")
        try:
            id_ = queryset.values('id')[0]
            name = queryset.values('job_name')[0]
            job_name = name.get('job_name')
            job_id = id_.get('id')
            trigger_name = JobList.objects.get(id=job_id).trigger.trigger_func
            if hasattr(JobAction, 'run_job'):
                func = getattr(JobAction, 'run_job')
                func(trigger_name, str(job_id))
            else:
                messages.error(request, '【启动错误】 ' + job_name + ' 任务不存在!')
            messages.success(request, '%s 任务启动成功' % job_name)
        except ConflictingIdError as e:
            logger.exception('任务启动冲突: %s', e)
            messages.error(request, job_name + ' 任务启动发生冲突！')
        except Exception as e:
            logger.exception('任务启动异常: %s', e)
            messages.error(request, job_name + ' 任务启动异常！<br/>请检查调度类型或执行频率')
        return messages

    action_job.short_description = '立即执行'
    action_job.icon = 'el-icon-video-play'
    action_job.type = 'warning'
    action_job.confirm = "确认立即执行？"
