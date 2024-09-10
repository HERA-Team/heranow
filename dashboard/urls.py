"""Definition of URLs for the project."""

from django.urls import include, path

from . import views
from .dash_apps import (
    adchists,
    autospectra,
    commissioning_issues,
    hex_notes,
    hex_plot,
    hookup_notes_table,
    node_plot,
    snapspectra,
)

app_name = "dashboard"

urlpatterns = [
    path("", views.home.as_view(), name="index"),
    path("spectra", views.AutoSpectraPlot.as_view(), name="spectra"),
    path("adchists", views.ADCHistograms.as_view(), name="adchists"),
    path("hex_stats", views.HexPlot.as_view(), name="hexplot"),
    path("node_stats", views.NodePlot.as_view(), name="nodeplot"),
    path("compute", views.CompterLoads.as_view(), name="compute"),
    path("librarian", views.LibrarianLogs.as_view(), name="librarian"),
    path(
        "librarian_completeness",
        views.LibarianTransfer.as_view(),
        name="librarian_completeness",
    ),
    path("qm", views.DailyQM.as_view(), name="qm"),
    path("hookup", views.ListHookup.as_view(), name="hookup"),
    path("snaphookup", views.SnapHookups.as_view(), name="snaphookup"),
    path("hookup_notes_table", views.NotesTable.as_view(), name="notestable"),
    path("hookup_notes", views.PerAntHookups.as_view(), name="hex_notes"),
    path("snapspectra", views.SnapSpectra.as_view(), name="snapspectra"),
    path("Grafana", views.Grafana.as_view(), name="grafana"),
    path("make_report", views.MakeReport.as_view(), name="make_report"),
    path("issue_log", views.IssueLog.as_view(), name="issue_log"),
    path("lightning", views.Lightning.as_view(), name="lightning"),
    path("Help", views.Help.as_view(), name="help"),
]
