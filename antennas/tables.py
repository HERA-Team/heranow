"""Definition of table used for CommissioningIssue page."""

import requests

import django_tables2 as tables
from django.utils.html import format_html
from .models import CommissioningIssue

notebook_link = (
    "https://github.com/HERA-Team/H3C_plots/blob/master/data_inspect_{}.ipynb"
)
issue_link = "https://github.com/HERA-Team/HERA_Commissioning/issues/{}"
new_issue_link = (
    "https://github.com/HERA-Team/HERA_Commissioning/issues"
    "/new?assignees=&labels=Daily&template=daily-log.md"
    "&title=Observing+report+{}"
)
rfi_link = (
    "https://github.com/alphatangojuliett/HERA_daily_RFI"
    "/blob/herapost-master/daily_RFI_report_{}.ipynb"
)

label_link = (
    "https://github.com/HERA-Team/HERA_Commissioning"
    + "/issues?q=is%3Aissue+is%3Aopen+label%3A{}"
)
notebook_view = notebook_link.replace("github.com", "nbviewer.jupyter.org/github")
rfi_view = rfi_link.replace("github.com", "nbviewer.jupyter.org/github")


class ComIssueTable(tables.Table):
    julian_date = tables.Column("Julian Date")
    related_issues = tables.Column("Related Issues")
    labels = tables.Column("Other Labels")
    notebook = tables.Column("Nightly Notebook", accessor="nightly_notebook_date")
    rfi = tables.Column("RFI Notebook", accessor="rfi_notebook_date")
    new_issues = tables.Column("New Issues Opened On This Day")

    class Meta:
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped"}

    def render_julian_date(self, value, record):
        return format_html(
            "<a target='_blank' href={}>{}</a>",
            issue_link.format(record.number),
            value,
        )

    def render_related_issues(self, value):
        return format_html(
            " ".join(
                format_html(
                    "<a target='_blank' href={}>{}</a>", issue_link.format(iss), iss
                )
                for iss in value
            )
        )

    def render_labels(eslf, value):
        return format_html(
            " ".join(
                format_html(
                    "<a target='_blank' href={}>{}</a>", label_link.format(label), label
                )
                for label in value
            )
        )

    def render_notebook(self, value):
        return format_html(
            "<a target='_blank' href={}>{}</a>", notebook_view.format(value), "View"
        )

    def render_rfi(self, value):
        return format_html(
            "<a target='_blank' href={}>{}</a>", rfi_view.format(value), "View"
        )
