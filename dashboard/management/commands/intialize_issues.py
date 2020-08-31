import re
import os
import copy
import github3
import logging  # noqa
import numpy as np
import pandas as pd
from astropy.time import Time
from dateutil import parser as dateparser
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand, CommandError

from heranow import settings
from dashboard.models import CommissioningIssue

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Read data from redis databse and update local django database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--key",
            dest="key",
            type=str,
            default=settings.GITHUB_APP_KEY_FILE,
            help="File where the app key is stored.",
        )
        parser.add_argument(
            "--appid",
            dest="appid",
            type=str,
            default=settings.GITHUB_APP_ID_FILE,
            help="File container github app id.",
        )

    def handle(self, *args, **options):

        with open(options["key"], "r") as key_file:
            key = key_file.read()
        with open(options["appid"], "r") as id_file:
            app_id = id_file.read()

        gh = github3.github.GitHub()
        gh.login_as_app(key.encode(), app_id)
        ap = gh.authenticated_app()
        inst = gh.app_installation_for_repository("HERA-Team", "HERA_Commissioning")
        gh.login_as_app_installation(key.encode(), ap.id, inst.id)
        repo = gh.repository("HERA-Team", "HERA_Commissioning")

        issues = repo.issues(labels="Daily", state="all")

        local_issue_regex = r"[^a-zA-Z0-9]#(\d+)"
        # the foreign issue reference may be useful in the future
        # foreign_issue_regex = r"[a-zA-Z0-9]#(\d+)"

        jd_list = []

        issue_list = []
        for cnt, issue in enumerate(issues):
            try:
                jd = int(issue.title.split(" ")[-1])
            except ValueError:
                match = re.search(r"\d{7}", issue.title)
                if match is not None:
                    jd = int(match.group())
                else:
                    continue
            jd_list.insert(0, jd)

            obs_date = Time(jd, format="jd")

            obs_date = timezone.make_aware(obs_date.datetime)
            obs_end = obs_date + timedelta(days=1)

            num_opened = len(
                list(repo.issues(state="all", sort="created", since=obs_date))
            ) - len(list(repo.issues(state="all", sort="created", since=obs_end)))

            other_labels = [lab.name for lab in issue.labels() if lab.name != "Daily"]
            iss_nums = map(int, re.findall(local_issue_regex, issue.body))
            related_issues = set()
            related_issues.update(iss_nums)
            for comm in issue.comments():
                nums = map(int, re.findall(local_issue_regex, issue.body))
                related_issues.update(nums)

            related_issues = sorted(related_issues)

            iss = CommissioningIssue(
                julian_date=jd,
                number=issue.number,
                related_issues=related_issues,
                labels=other_labels,
                new_issues=num_opened,
            )
            issue_list.append(iss)

        CommissioningIssue.objects.bulk_create(issue_list)

        jd_list = np.sort(jd_list).astype(int)
        full_jd_range = np.arange(jd_list.min(), int(np.floor(Time.now().jd)) + 1)

        new_issues = []
        for jd in np.setdiff1d(full_jd_range, jd_list):
            iss = CommissioningIssue(julian_date=jd,)
            new_issues.append(iss)

        CommissioningIssue.objects.bulk_create(new_issues)
