"""A dash app to plot snapspectra."""

import re
import uuid
import numpy as np
import pandas as pd

from functools import lru_cache

import dash
import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from dashboard.models import SnapSpectra, SnapStatus, AntennaStatus


def plot_df(df, hostname):
    """Plot input dataframe for Snap Spectra.

    Parameters
    ----------
    df : Pandas DataFrame
        data from hosting adc histogram data from get_data
    hostname : String
        HERA snap hostname to plot spectra

    Returns
    -------
    plotly Figure object

    """
    layout = {
        "xaxis": {
            "title": "Frequency [MHz]",
            "showticklabels": True,
            "tick0": 0,
            "dtick": 10,
        },
        "yaxis": {"title": "Power [dB]", "showticklabels": True,},
        "hoverlabel": {"align": "left"},
        "margin": {"l": 40, "b": 30, "r": 40, "t": 30},
        "autosize": True,
        "showlegend": True,
        "hovermode": "closest",
        "legend": {"title": "ADC Port # : Antpol"},
        "uirevision": hostname,
    }

    fig = go.Figure()
    fig.layout = layout

    df1 = df[df.hostname == hostname]
    for loc_num in sorted(df1.loc_num.unique()):
        df2 = df1[df1.loc_num == loc_num]
        trace = go.Scatter(
            x=df2.freqs,
            y=df2.spectra,
            name=f"{loc_num}: {df2.mc_name.iloc[0]}",
            hovertemplate="%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]",
            mode="lines",
        )
        fig.add_trace(trace)

    return fig


@lru_cache(maxsize=32)
def get_data(session_id, interval):
    """Query Database and prepare data as DataFrame.

    Parameters
    ----------
    session_id : str
        unique session id hex used for caching.
    interval : int
        update interval from counter used for updating data.

    Returns
    -------
    df : pandas DataFrame
        most recent statistics for each antpol.
    dropdown_labels : Dict
        Dictionary of list used as child divs for a Dash dropdown label. Keyed by label name.

    """
    data = []
    for unique_hosts in (
        SnapSpectra.objects.values("hostname", "input_number").distinct().iterator()
    ):
        hostname = unique_hosts["hostname"]
        loc_num = unique_hosts["input_number"]
        match = re.search(r"heraNode(?P<node>\d+)Snap(?P<snap>\d+)", hostname)
        node = int(match.group("node"))
        snap = int(match.group("snap"))

        last_spectra = SnapSpectra.objects.filter(
            hostname=hostname, input_number=loc_num
        ).latest("time")
        spectra = np.atleast_1d(
            np.ma.masked_invalid(
                10
                * np.log10(
                    np.asarray(last_spectra.spectra, dtype=np.float64)
                    / np.asarray(last_spectra.eq_coeffs, dtype=np.float64) ** 2
                )
            ).filled(-100)
        )
        mc_name = "Unknown"
        try:
            ant_stat = AntennaStatus.objects.filter(
                snap_hostname=hostname, snap_channel_number=loc_num
            ).latest("time")
        except AntennaStatus.DoesNotExist:
            ant_stat = None
        if ant_stat is not None:
            mc_name = f"{ant_stat.antenna.ant_number}{ant_stat.antenna.polarization}"
        freqs = np.linspace(0, 250, spectra.size)
        data.append(
            pd.DataFrame(
                {
                    "time": last_spectra.time,
                    "hostname": hostname,
                    "loc_num": loc_num,
                    "node": node,
                    "snap": snap,
                    "mc_name": mc_name,
                    "spectra": spectra,
                    "freqs": freqs,
                }
            )
        )

    df = pd.concat(data)
    if not df.empty:
        df.sort_values(
            ["node", "snap", "loc_num", "freqs"], ignore_index=True, inplace=True
        )

    dropdown_labels = {}
    hostlist = df.hostname.unique()
    for hostname in hostlist:
        try:
            stat = SnapStatus.objects.filter(hostname=hostname).latest("time")
        except SnapStatus.DoesNotExist:
            stat = None
        if stat is not None:
            label = [
                dcc.Markdown(
                    f"""
                    {hostname}
                    programmed: **{stat.last_programmed_time.isoformat(' ')}**
                    spectra recorded: **{stat.time.isoformat(' ')}**
                    temp: {stat.fpga_temp:.1f}C  pps count: {stat.pps_count} Cycles uptime: {stat.uptime_cycles}
                    """,
                    style={"display": "block", "white-space": "pre"},
                ),
            ]

        else:
            label = [
                dcc.Markdown(
                    f"""
                    {hostname}
                    Statistics Unknown
                    """,
                    tyle={"display": "block", "white-space": "pre"},
                ),
            ]

        dropdown_labels.update({hostname: label})

    return df, dropdown_labels


def serve_layout():
    """Render layout of webpage.

    Returns
    -------
    Div of application used in web rendering.

    """
    session_id = str(uuid.uuid4())
    return html.Div(
        [
            html.Div(session_id, id="session-id", style={"display": "none"}),
            dbc.Row(
                [
                    dbc.Col(
                        daq.BooleanSwitch(
                            id="reload-box",
                            on=False,
                            label="Reload Data",
                            labelPosition="top",
                        ),
                        width=1,
                    ),
                    html.Label(
                        [
                            "Snap:",
                            dcc.Dropdown(
                                id="hostname-dropdown",
                                options=[],
                                multi=False,
                                clearable=False,
                                style={"width": "100%", "display": "inline-block"},
                            ),
                        ],
                        style={"width": "15%"},
                    ),
                    html.Div(
                        # children=dropdown_labels[hostlist[0]],
                        id="snap-stats",
                        style={"padding-left": "1em"},
                    ),
                ],
                justify="center",
                align="center",
            ),
            dcc.Graph(
                # figure=plot_df(df, hostname=hostlist[0]),
                id="dash_app",
                config={"doubleClick": "reset"},
                style={"height": "72.5vh"},
            ),
            dcc.Interval(
                id="interval-component",
                interval=60 * 1000,
                n_intervals=0,
                disabled=True,
            ),
        ],
        style={"height": "100%", "width": "100%"},
    )


app_name = "dash_snapsepctra"

dash_app = DjangoDash(
    name=app_name,
    serve_locally=False,
    app_name=app_name,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    add_bootstrap_links=True,
)


dash_app.layout = serve_layout


@dash_app.callback(
    Output("interval-component", "disabled"), [Input("reload-box", "on")],
)
def start_reload_counter(reload_box):
    """Track the reload status for data."""
    return not reload_box


@dash_app.callback(
    Output("hostname-dropdown", "options"),
    [Input("session-id", "children"), Input("interval-component", "n_intervals")],
)
def update_snap_selection(session_id, n_intervals):
    """Re-compute snap dropdown options."""
    df, dropdown_labels = get_data(session_id, n_intervals)
    options = [{"label": host, "value": host} for host in dropdown_labels.keys()]
    return options


@dash_app.callback(
    [Output("dash_app", "figure"), Output("snap-stats", "children"),],
    [
        Input("hostname-dropdown", "value"),
        Input("session-id", "children"),
        Input("interval-component", "n_intervals"),
    ],
)
def redraw_statistic(hostname, session_id, n_intervals):
    """Replot the spectra based on user input."""
    df, dropdown_labels = get_data(session_id, n_intervals)
    if hostname is None:
        hostname = list(dropdown_labels.keys())[0]
    return plot_df(df, hostname=hostname), dropdown_labels[hostname]
