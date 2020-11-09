"""A dash application to plot adchistograms."""
import re

import copy
import uuid
import numpy as np
import pandas as pd

from astropy.time import Time
from functools import lru_cache

import dash
import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from ..models import Antenna, AntennaStatus, AprioriStatus


def plot_df(df, nodes=None, apriori=None):
    """Plot input dataframe for adc histograms.

    Parameters
    ----------
    df : Pandas DataFrame
        data from hosting adc histogram data from get_data
    nodes : List of int or int
        Specific nodes to plot
    apriori: List of str or str
        Specific apriori statuses to plot.

    Returns
    -------
    plotly Figure object

    """
    hovertemplate = "(%{x:.1},\t%{y})<br>%{fullData.text}<extra>%{fullData.name}<br>Node: %{meta[0]}<br>Status: %{meta[1]}</extra>"
    if nodes is not None and isinstance(nodes, str):
        nodes = [nodes]
    elif nodes is None or len(nodes) == 0:
        nodes = df.node.unique()

    if apriori is not None and isinstance(apriori, str):
        apriori = [apriori]
    elif apriori is None or len(apriori) == 0:
        apriori = df.apriori.unique()

    layout = {
        "xaxis": {"title": "ADC value"},
        "yaxis": {"title": "Occurance", "type": "linear"},
        "title": {
            "text": "ADC Histograms",
            "xref": "paper",
            "x": 0.5,
            "font": {"size": 24,},
        },
        "margin": {"l": 40, "b": 30, "r": 40, "t": 70},
        "hovermode": "closest",
        "autosize": True,
        "showlegend": True,
    }

    fig = go.Figure()

    if "bins" not in df and "adchist" not in df:
        return fig

    fig["layout"] = layout
    fig["layout"]["uirevision"] = f"{nodes} {apriori}"
    for ant in df.ant.unique():
        _df_ant = df[df.ant == ant]

        for pol in _df_ant.pol.unique():
            antpol = f"{ant}{pol}"
            _df1 = _df_ant[_df_ant.pol == pol]
            if _df1.node.iloc[0] not in nodes or _df1.apriori.iloc[0] not in apriori:
                continue
            timestamp = Time(_df1.time.iloc[0], format="datetime")
            trace = go.Scatter(
                x=_df1.bins,
                y=_df1.adchist,
                name=antpol,
                mode="lines",
                hovertemplate=hovertemplate,
                text=f"observed at {timestamp.iso}<br>(JD {timestamp.jd:.3f})",
                meta=[_df1.node.iloc[0], _df1.apriori.iloc[0]],
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
    pandas DataFrame of most recent ADC Histograms for each antpol.

    """
    df = []

    for antenna in Antenna.objects.all().iterator():
        try:
            stat = AntennaStatus.objects.filter(antenna=antenna).latest("time")
        except AntennaStatus.DoesNotExist:
            stat = None

        if stat is not None:
            node = "Unknown"
            match = re.search(r"heraNode(?P<node>\d+)Snap", stat.snap_hostname)
            if match is not None:
                node = int(match.group("node"))

            apriori = "Unknown"
            try:
                apriori_stat = AprioriStatus.objects.filter(
                    antenna=stat.antenna
                ).latest("time")
            except AprioriStatus.DoesNotExist:
                apriori_stat = None
            if apriori_stat is not None:
                apriori = apriori_stat.get_apriori_status_display()
            if stat.adc_hist is not None:
                df.extend(
                    {
                        "bins": b,
                        "adchist": h,
                        "ant": stat.antenna.ant_number,
                        "pol": f"{stat.antenna.polarization}",
                        "node": node,
                        "apriori": apriori,
                        "time": stat.time,
                    }
                    for b, h in zip(*stat.adc_hist)
                )

    df = pd.DataFrame(df)
    # Sort according to increasing bins and antpols
    if not df.empty:
        df.sort_values(["ant", "pol"], inplace=True)
        df.reset_index(drop=True, inplace=True)

    return df


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
                            "Node(s):",
                            dcc.Dropdown(
                                id="node-dropdown",
                                options=[{"label": "Unknown Node", "value": "Unknown"}],
                                multi=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "30%"},
                    ),
                    html.Label(
                        [
                            "Apriori Status(es):",
                            dcc.Dropdown(
                                id="apriori-dropdown",
                                options=[
                                    {
                                        "label": f"{str(apriori[1])}",
                                        "value": str(apriori[1]),
                                    }
                                    for apriori in AprioriStatus.AprioriStatusList.choices
                                ]
                                + [{"label": "Unknown", "value": "Unknown"}],
                                multi=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "30%"},
                    ),
                ],
                justify="center",
                align="center",
            ),
            dcc.Graph(
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


app_name = "dash_adchists"

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
    Output("node-dropdown", "options"),
    [Input("session-id", "children"), Input("interval-component", "n_intervals")],
)
def update_node_selection(session_id, n_intervals):
    """Update node selection button."""
    df = get_data(session_id, n_intervals)
    node_labels = [
        {"label": f"Node {node}", "value": node}
        for node in sorted([node for node in df.node.unique() if node != "Unknown"])
    ] + [{"label": "Unknown Node", "value": "Unknown"}]
    return node_labels


@dash_app.callback(
    Output("dash_app", "figure"),
    [
        Input("dash_app", "relayoutData"),
        Input("node-dropdown", "value"),
        Input("apriori-dropdown", "value"),
        Input("session-id", "children"),
        Input("interval-component", "n_intervals"),
    ],
)
def draw_undecimated_data(
    selection, node_value, apriori_value, session_id, n_intervals
):
    """Redraw data based on user input."""
    df = get_data(session_id, n_intervals)
    return plot_df(df, node_value, apriori_value)
