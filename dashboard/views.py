"""Definition of each page's view."""
import socket
import logging

from tabination.views import TabView
from django.shortcuts import redirect

from dashboard.models import AntToSnap, SnapToAnt, XengChannels

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


class DashChildTab(ChildTab):
    """Render class for Dash Apps which appear as dropdown children."""

    app_name = ""
    template_name = "plotly_direct.html"

    def get_context_data(self, **kwargs):
        """Add data to page context."""
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context["app_name"] = self.app_name
        return context


class ExternalTab(BaseTab):
    """Base class for external redirect."""

    external = True
    url = ""

    def get(self, request):
        """Return redirect when GETing the page."""
        return redirect(self.url)


class ExternalChildTab(ChildTab):
    """Base Class for child tabs that are external redirects."""

    external = True
    url = ""

    def get(self, request):
        """Return redirect when GETing the page."""
        return redirect(self.url)


class home(BaseTab):
    """The home-page. Should just be simple html with links to what to do."""

    _is_tab = False
    template_name = "index.html"


class AutoSpectraPlot(DashChildTab):
    """Link to autospectra."""

    tab_label = "Autospectra"
    tab_id = "spectra"
    app_name = "dash_autospectra"


class ADCHistograms(DashChildTab):
    """Link to ADC histograms."""

    tab_label = "ADC Histograms"
    tab_id = "adchists"
    app_name = "dash_adchists"


class HexPlot(DashChildTab):
    """Link to Stats by Hex plot."""

    tab_label = "Statistics by Hex Position"
    tab_id = "hex_stats"
    app_name = "dash_hexplot"


class NodePlot(DashChildTab):
    """Link to Stats by Hex plot."""

    tab_label = "Statistics by Node"
    tab_id = "node_stats"
    app_name = "dash_nodeplot"


class LibrarianLogs(ExternalChildTab):
    """Link to Librarian Logs."""

    tab_label = "Librarian Logs"
    tab_id = "librarian"
    url = "https://enterprise.sese.asu.edu:8484/d/w6B2klSMk/librarian"


class LibrarianTracker(ChildTab):
    """Link to Librarian File Tracker."""

    tab_label = "Librarian File Tracker"
    tab_id = "librariancheck"


class CompterLoads(ExternalChildTab):
    """Link to Computer Loads."""

    tab_label = "Compter Loads"
    tab_id = "compute"
    url = "https://enterprise.sese.asu.edu:8484/d/LDl5uQIMk/compute"


class DailyQM(ExternalChildTab):
    """Link to ADC histograms."""

    tab_label = "Daily Quality Metrics"
    tab_id = "qm"
    url = "https://enterprise.sese.asu.edu:8484/d/el0JGlIGk/quality-metrics"


class SnapSpectra(DashChildTab):
    """Link to QM Metrics."""

    tab_label = "SNAP Spectra"
    tab_id = "snapspectra"
    app_name = "dash_snapsepctra"


class DetailedPages(BaseTab):
    """A detailed list of pages in heranow."""

    tab_label = "Detailed HERA now pages"
    my_children = [
        "librarian",
        "librariancheck",
        "hex_stats",
        "node_stats",
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


class Notebooks(BaseTab):
    """A detailed list of pages in heranow."""

    tab_label = "Notebook listings"
    my_children = ["notebooks", "GithubNotebooks"]


class NotebooksSelf(ChildTab):
    """Link to self Notebooks hoster."""

    tab_label = "Self-Hosted"
    tab_id = "notebooks"


class NotebooksGit(ExternalChildTab):
    """Link to daily Notebooks."""

    tab_label = "Github Notebooks"
    tab_id = "GithubNotebooks"
    url = "https://github.com/HERA-Team/H6C_Notebooks"


class DailyLog(ExternalChildTab):
    """Link to new Daily Log Commissioning Report."""

    tab_label = "H6C Obs Report"
    tab_id = "DailyLog"
    url = "https://docs.google.com/forms/d/e/1FAIpQLScWHCiy5j6x5Lkwqoe5YOPhCyFpulVrUDfCHG90Jyvygal7zA/viewform"


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
    template_name = "included_page.html"

    def get_context_data(self, **kwargs):
        """Add executing hostname to context."""
        context = super().get_context_data(**kwargs)
        context["sub_page"] = "sys_conn_tmp.html"
        return context


class PerAntHookups(DashChildTab):
    """Link cable hookups."""

    tab_label = "Per Antenna Hookup Notes"
    tab_id = "hookup_notes"
    app_name = "dash_hex_notes"


class NotesTable(DashChildTab):
    """Link cable hookups."""

    tab_label = "Table of Hookup Notes"
    tab_id = "hookup_notes_table"
    app_name = "dash_hookup_notes"
    template_name = "plotly_direct_table.html"


class SnapHookups(ChildTab):
    """Link cable hookups."""

    tab_label = "SNAP Hookup Listing"
    tab_id = "snaphookup"
    template_name = "snaphookup.html"

    def get_context_data(self, **kwargs):
        """Add executing hostname to context."""
        context = super().get_context_data(**kwargs)
        last_xeng_time = XengChannels.objects.last().time
        last_mapping_time = AntToSnap.objects.last().time
        context["xengs"] = XengChannels.objects.filter(time=last_xeng_time).order_by(
            "number"
        )
        context["ants"] = AntToSnap.objects.filter(time=last_mapping_time).order_by(
            "antenna__ant_number"
        )
        context["snaps"] = SnapToAnt.objects.filter(time=last_mapping_time).order_by(
            "node", "snap"
        )
        return context


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


class Crons(BaseTab):
    """Cron job dumps."""

    tab_label = "Cronjobs"
    tab_id = "cronjobs"


class IssueLog(DashChildTab):
    """Commissioning Issue Log."""

    tab_label = "Issue Log"
    tab_id = "issue_log"
    _is_tab = True
    top = True
    template_name = "plotly_direct_table.html"
    app_name = "dash_commissioning_issue"


class Help(ExternalTab):
    """Help me."""

    tab_label = "Help"
    tab_id = "Help"
    url = "http://hera.pbworks.com/w/page/117456570/Commissioning"
