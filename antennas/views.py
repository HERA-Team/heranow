import socket
import logging


from tabination.views import TabView
from django.shortcuts import redirect

from .models import AntennaStatus
from .plotting_scripts import autospectra

logger = logging.getLogger(__name__)
# Create your views here.


class BaseTab(TabView):
    """Base class for all main navigation tabs."""

    _is_tab = True
    tab_group = "main"
    top = True

    def get_context_data(self, **kwargs):
        """Add executing hostname to context."""
        context = super().get_context_data(**kwargs)
        context["hostname"] = socket.gethostname()
        return context


class ChildTab(BaseTab):
    """Base class for children tabs in dropdowns."""

    _is_tab = False
    top = False
    tab_group = "main"


class ExternalTab(BaseTab):
    """Base class for external redirect."""

    external = True
    url = ""

    def get(self, request):
        return redirect(self.url)


class ExternalChildTab(ChildTab):
    """Base Class for child tabs that are external redirects."""

    external = True
    url = ""

    def get(self, request):
        return redirect(self.url)


class home(BaseTab):
    """The home-page. Should just be simple html with links to what to do."""

    _is_tab = False
    template_name = "index.html"


class AutoSpectra(ChildTab):
    """Link to autospectra."""

    tab_label = "Autospectra"
    tab_id = "spectra"
    template_name = "autospectra.html"

    def get_context_data(self, **kwargs):
        """Add auto spectra from the Antenna Status table to context."""
        context = super().get_context_data(**kwargs)
        last_status = AntennaStatus.objects.last()
        if last_status is not None:
            all_stats = AntennaStatus.objects.filter(time=last_status.time).all()
            div = autospectra.make_plot(all_stats)

            context["plotly_div"] = div

        return context


class ADCHistograms(ChildTab):
    """Link to ADC histograms."""

    tab_label = "ADC Histograms"
    tab_id = "adchists"


class LibrarianLogs(ChildTab):
    """Link to ADC histograms."""

    tab_label = "Librarian Logs"
    tab_id = "librarian"


class LibrarianTracker(ChildTab):
    """Link to ADC histograms."""

    tab_label = "Librarian File Tracker"
    tab_id = "librariancheck"


class CompterLoads(ChildTab):
    """Link to ADC histograms."""

    tab_label = "Compter Loads"
    tab_id = "compute"


class DailyQM(ChildTab):
    """Link to ADC histograms."""

    tab_label = "Daily Quality Metrics"
    tab_id = "qm"


class SNAPSpectra(ChildTab):
    """Link to ADC histograms."""

    tab_label = "SNAP Spectra"
    tab_id = "snapspectra"


class DetailedPages(BaseTab):
    """A detailed list of pages in heranow."""

    tab_label = "Detailed HERA now pages"
    my_children = [
        "librarian",
        "librariancheck",
        "spectra",
        "adchists",
        "compute",
        "qm",
        "snapspectra",
    ]


class Chronograf(ExternalChildTab):
    """Link to external Chronograf."""

    tab_label = "Chronograf"
    tab_id = "Chronograf"
    url = "https://galileo.sese.asu.edu:8888/"


class Grafana(ExternalChildTab):
    """Link to external Grafana."""

    tab_label = "Grafana"
    tab_id = "Grafana"
    url = "https://enterprise.sese.asu.edu:8484"


class TimeDomain(BaseTab):
    """Link to time-domain data."""

    tab_label = "Time Domain Data"
    my_children = ["Grafana", "Chronograf"]


class Notebooks(ExternalTab):
    """Link to daily Notebooks."""

    tab_label = "Daily Notebooks"
    tab_id = "Notebooks"
    url = "https://github.com/HERA-Team/H3C_plots"


class DailyLog(ExternalChildTab):
    """Link to new Daily Log Commissioning Issues."""

    tab_label = "New Daily Log"
    tab_id = "DailyLog"
    url = (
        "https://github.com/HERA-Team/HERA_Commissioning/issues/"
        "new?assignees=&labels=Daily&template=daily-log.md&"
        "title=Observing+report+2458XXX"
    )


class NewIssue(ExternalChildTab):
    """Link to new generic Commissioning Issue."""

    tab_label = "New Issue"
    tab_id = "NewIssue"
    url = "https://github.com/HERA-Team/HERA_Commissioning/issues/new"


class MakeReport(BaseTab):
    """List External issues."""

    tab_label = "Make A Report"
    my_children = ["DailyLog", "NewIssue"]


class ListHookup(ChildTab):
    """Link cable hookups."""

    tab_label = "Cable Hookup Listings"
    tab_id = "hookup"


class PerAntHookups(ChildTab):
    """Link cable hookups."""

    tab_label = "Per Antenna Hookup Notes"
    tab_id = "hookup_notes"


class TableHookups(ChildTab):
    """Link cable hookups."""

    tab_label = "Table of Hookup Notes"
    tab_id = "hookup_notes_table"


class SnapHookups(ChildTab):
    """Link cable hookups."""

    tab_label = "SNAP Hookup Listing"
    tab_id = "snaphookup"


class Hookups(BaseTab):
    """Dropdown for hookup types."""

    tab_label = "Hookup Listings"
    tab_id = "hookup_listings"
    my_children = [
        "hookup",
        "hookup_notes",
        "hookup_notes_table",
        "snaphookup",
    ]


class Help(ExternalTab):
    """Help me."""

    tab_label = "Help"
    tab_id = "Help"
    url = "http://hera.pbworks.com/w/page/117456570/Commissioning"
