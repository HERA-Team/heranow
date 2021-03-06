"""Definition of URLs for the project."""
from django.urls import path, include

from . import views
from .dash_apps import (
    autospectra,
    adchists,
    hex_plot,
    node_plot,
    snapspectra,
    hookup_notes_table,
    hex_notes,
    commissioning_issues,
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
    path("qm", views.DailyQM.as_view(), name="qm"),
    path("hookup", views.ListHookup.as_view(), name="hookup"),
    path("snaphookup", views.SnapHookups.as_view(), name="snaphookup"),
    path("hookup_notes_table", views.NotesTable.as_view(), name="notestable"),
    path("hookup_notes", views.PerAntHookups.as_view(), name="hex_notes"),
    path("snapspectra", views.SnapSpectra.as_view(), name="snapspectra"),
    path("Chronograf", views.Chronograf.as_view(), name="chronograf"),
    path("Grafana", views.Grafana.as_view(), name="grafana"),
    path("Notebooks", views.Notebooks.as_view(), name="notebooks"),
    path("DailyLog", views.DailyLog.as_view(), name="dailylogs"),
    path("NewIssue", views.NewIssue.as_view(), name="newissues"),
    path("issue_log", views.IssueLog.as_view(), name="issue_log"),
    path("Help", views.Help.as_view(), name="help"),
]
