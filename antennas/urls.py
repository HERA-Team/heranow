from django.urls import path

from . import views

app_name = "antennas"

urlpatterns = [
    path("", views.home.as_view(), name="index"),
    path("spectra", views.AutoSpectra.as_view(), name="spectra"),
    path("Chronograf", views.Chronograf.as_view(), name="chronograf"),
    path("Grafana", views.Grafana, name="chronograf"),
    path("Notebooks", views.Notebooks.as_view(), name="notebooks"),
    path("DailyLog", views.DailyLog.as_view(), name="notebooks"),
    path("NewIssue", views.NewIssue.as_view(), name="notebooks"),
    path("Help", views.Help.as_view(), name="notebooks"),
]
