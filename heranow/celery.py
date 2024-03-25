"""Celery app construction and task scheduling."""

import os

from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "heranow.settings")

app = Celery("heranow")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "get_autocorrelations": {
        "task": "dashboard.tasks.get_autospectra_from_redis",
        "schedule": crontab(),
        "args": (),
    },
    "get_snap_spectra": {
        "task": "dashboard.tasks.get_snap_spectra_from_redis",
        "schedule": crontab(),
        "args": (),
    },
    "get_snap_status": {
        "task": "dashboard.tasks.get_snap_status_from_redis",
        "schedule": crontab(),
        "args": (),
    },
    "update_hookup_notes": {
        "task": "dashboard.tasks.update_hookup_notes",
        "schedule": crontab(hour="*/6", minute=0),
        "args": (),
    },
    "get_ant_status": {
        "task": "dashboard.tasks.get_antenna_status_from_redis",
        "schedule": crontab(),
        "args": (),
    },
    "update_constructed_antennas": {
        "task": "dashboard.tasks.update_constructed_antennas",
        "schedule": crontab(hour=0, minute=0),
        "args": (),
    },
    "update_apriori": {
        "task": "dashboard.tasks.update_apriori",
        "schedule": crontab(minute=0),
        "args": (),
    },
    "update_issue_log": {
        "task": "dashboard.tasks.update_issue_log",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": (),
    },
    "replot_radiosky": {
        "task": "dashboard.tasks.replot_radiosky",
        "schedule": crontab(),
        "args": (),
    },
    "update_hookup": {
        "task": "dashboard.tasks.update_hookup",
        "schedule": crontab(minute=0, hour="*/12"),
        "args": (),
    },
    "update_xengs": {
        "task": "dashboard.tasks.update_xengs",
        "schedule": crontab(minute=0),
        "args": (),
    },
    "update_ant_to_snap": {
        "task": "dashboard.tasks.update_ant_to_snap",
        "schedule": crontab(minute=0),
        "args": (),
    },
    "update_snap_to_ant": {
        "task": "dashboard.tasks.update_snap_to_ant",
        "schedule": crontab(minute=0),
        "args": (),
    },
    "update_ant_csv": {
        "task": "dashboard.tasks.antenna_stats_to_csv",
        "schedule": crontab(minute="*/5"),
        "args": (),
    },
    # delete data older than 2 months.
    "delete_old_data": {
        "task": "dashboard.tasks.delete_old_data",
        "schedule": crontab(minute=0, hour=0),
        "args": (),
    },
}
