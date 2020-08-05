from django.urls import path, include

from . import views
from .dash_apps import autospectra

app_name = "antennas"

urlpatterns = [
    path("", views.home.as_view(), name="index"),
    path("spectra", views.AutoSpectra.as_view(), name="spectra"),
    path("adchists", views.ADCHistograms.as_view(), name="adchists"),
    path("Chronograf", views.Chronograf.as_view(), name="chronograf"),
    path("Grafana", views.Grafana.as_view(), name="grafana"),
    path("Notebooks", views.Notebooks.as_view(), name="notebooks"),
    path("DailyLog", views.DailyLog.as_view(), name="dailylogs"),
    path("NewIssue", views.NewIssue.as_view(), name="newissues"),
    path("Help", views.Help.as_view(), name="help"),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
]
