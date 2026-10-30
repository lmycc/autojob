"""
WSGI config for autojob project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autojob.settings')

application = get_wsgi_application()
try:
    from app import job_tool
    from app.management.commands.scan_jobs import Command

    job_tool.job_control()

    scan_jobs = Command()
    scan_jobs.handle()
except ImportError:
    pass
