"""A dash application to plot autospectra."""
import re

import uuid
import copy
import numpy as np
import pandas as pd
from itertools import product
from functools import lru_cache

from astropy.time import Time

import lttb

import dash
import dash_daq as daq
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from ..models import AutoSpectra, AntennaStatus, AprioriStatus

max_points = 4000


@lru_cache
def get_data(session_id, interval):
    df_full = []
    df_down = []

    last_spectra = AutoSpectra.objects.last()
    if last_spectra is not None:
        auto_time = Time(last_spectra.time, format="datetime")

        for stat in AutoSpectra.objects.filter(time=last_spectra.time).order_by(
            "antenna"
        ):
            ant_stat = (
                AntennaStatus.objects.filter(antenna=stat.antenna)
                .order_by("time")
                .last()
            )
            node = "Unknown"
            if ant_stat is not None:
                match = re.search(r"heraNode(?P<node>\d+)Snap", ant_stat.snap_hostname)
                if match is not None:
                    node = int(match.group("node"))

            apriori = "Unknown"
            apriori_stat = (
                AprioriStatus.objects.filter(antenna=stat.antenna)
                .order_by("time")
                .last()
            )
            if apriori_stat is not None:
                apriori = apriori_stat.get_apriori_status_display()

            _spectra = stat.spectra
            if stat.eq_coeffs is not None:
                _spectra /= np.median(stat.eq_coeffs) ** 2

            _freqs = np.asarray(stat.frequencies) / 1e6
            _spectra = (10 * np.log10(np.ma.masked_invalid(_spectra))).filled(-100)

            df_full.append(
                pd.DataFrame(
                    {
                        "freqs": _freqs,
                        "spectra": _spectra,
                        "ant": stat.antenna.ant_number,
                        "pol": f"{stat.antenna.polarization}",
                        "node": node,
                        "apriori": apriori,
                    }
                )
            )

            _d_spectra = stat.spectra_downsampled
            if stat.eq_coeffs is not None:
                _d_spectra /= np.median(stat.eq_coeffs) ** 2

            _d_freqs = np.asarray(stat.frequencies_downsampled) / 1e6
            _d_spectra = (10 * np.log10(np.ma.masked_invalid(_d_spectra))).filled(-100)

            df_down.append(
                pd.DataFrame(
                    {
                        "freqs": _d_freqs,
                        "spectra": _d_spectra,
                        "ant": stat.antenna.ant_number,
                        "pol": f"{stat.antenna.polarization}",
                        "node": node,
                        "apriori": apriori,
                    }
                )
            )

    else:
        auto_time = Time(0, format="jd")
    df_full = pd.concat(df_full)
    df_down = pd.concat(df_down)
    if not df_full.empty:
        # Sort according to increasing frequencies and antpols
        df_full.sort_values(["freqs", "ant", "pol"], inplace=True)
        df_down.sort_values(["freqs", "ant", "pol"], inplace=True)
        df_full.reset_index(drop=True, inplace=True)
        df_down.reset_index(drop=True, inplace=True)

    return df_full, df_down, auto_time


def plot_df(df, nodes=None, apriori=None):

    if nodes is not None and isinstance(nodes, str):
        nodes = [nodes]
    elif nodes is None or len(nodes) == 0:
        nodes = df.node.unique()

    if apriori is not None and isinstance(apriori, str):
        apriori = [apriori]
    elif apriori is None or len(apriori) == 0:
        apriori = df.apriori.unique()

    hovertemplate = (
        "%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]"
        "<extra>%{fullData.name}<br>Node: %{meta[0]}<br>Status: %{meta[1]}</extra>"
    )

    layout = {
        "xaxis": {"title": "Frequency [MHz]"},
        "yaxis": {"title": "Power [dB]"},
        "title": {
            "text": "Autocorrelations",
            "xref": "paper",
            "x": 0.5,
            "font": {"size": 24},
        },
        "autosize": True,
        "showlegend": True,
        "legend": {"x": 1, "y": 1},
        "margin": {"l": 40, "b": 30, "r": 40, "t": 46},
        "hovermode": "closest",
    }

    fig = go.Figure()

    if "freqs" not in df and "spectra" not in df:
        return fig

    fig["layout"] = layout
    fig["layout"]["uirevision"] = f"{nodes}-{apriori}"
    for ant in df.ant.unique():
        _df_ant = df[df.ant == ant]

        for pol in _df_ant.pol.unique():
            antpol = f"{ant}{pol}"
            _df1 = _df_ant[_df_ant.pol == pol]
            if _df1.node.iloc[0] not in nodes or _df1.apriori.iloc[0] not in apriori:
                continue
            trace = go.Scatter(
                x=_df1.freqs,
                y=_df1.spectra,
                name=antpol,
                mode="lines",
                meta=[_df1.node.iloc[0], _df1.apriori.iloc[0]],
                hovertemplate=hovertemplate,
            )
            fig.add_trace(trace)
    return fig


def serve_layout():
    timestamp = Time(0, format="jd")
    init_time_ago = (Time.now() - timestamp).to("min")
    init_time_color = "red"
    session_id = str(uuid.uuid4())

    return html.Div(
        [
            html.Div(session_id, id="session-id", style={"display": "none"}),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            id="auto-time",
                            children=[
                                html.Span(
                                    "Autocorrelations from ",
                                    style={"font-weight": "bold"},
                                ),
                                html.Span(
                                    f"{init_time_ago.value:.0f} {init_time_ago.unit.long_names[0]}s ago ",
                                    style={
                                        "font-weight": "bold",
                                        "color": init_time_color,
                                    },
                                ),
                                html.Span(
                                    f"({timestamp.iso} JD:{timestamp.jd:.3f})",
                                    style={"font-weight": "bold"},
                                ),
                            ],
                            style={"text-align": "center"},
                        ),
                        width=10,
                    ),
                ],
                justify="center",
                align="center",
                style={"height": "10%"},
            ),
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
                                    {"label": f"{apriori[1]}", "value": apriori[0]}
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
                style={"height": "10%"},
            ),
            dcc.Graph(
                id="dash_app", config={"doubleClick": "reset"}, style={"height": "80%"},
            ),
            # A timer to re-load data every minute
            # interval value is milliseconds
            dcc.Interval(
                id="interval-component",
                interval=60 * 1000,
                n_intervals=0,
                disabled=True,
            ),
            dcc.Interval(
                id="time-display-interval-component",
                interval=60 * 1000,
                n_intervals=0,
                disabled=False,
            ),
        ],
        style={"height": "100%", "width": "100%"},
    )


app_name = "dash_autospectra"

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
    return not reload_box


@dash_app.callback(
    Output("auto-time", "children"),
    [
        Input("session-id", "children"),
        Input("interval-component", "n_intervals"),
        Input("time-display-interval-component", "n_intervals"),
    ],
)
def update_time_data(session_id, n_intervals, n_intervals_time_display):
    df_full, df_down, auto_time = get_data(session_id, n_intervals)

    time_ago = (Time.now() - auto_time).to("min")

    if time_ago.value > 10:
        time_color = "red"
    else:
        time_color = "black"

    if time_ago.value > 60:
        time_ago = time_ago.to("hour")
    if time_ago.value > 24:
        time_ago = time_ago.to("day")

    time_data = [
        html.Span("Autocorrelations from ", style={"font-weight": "bold"}),
        html.Span(
            f"{time_ago.value:.0f} {time_ago.unit.long_names[0]}s ago ",
            style={"font-weight": "bold", "color": time_color,},
        ),
        html.Span(
            f"({auto_time.iso} JD:{auto_time.jd:.3f})", style={"font-weight": "bold"},
        ),
    ]
    return time_data


@dash_app.callback(
    Output("node-dropdown", "options"),
    [Input("session-id", "children"), Input("interval-component", "n_intervals")],
)
def update_node_selection(session_id, n_intervals):
    df_full, df_down, auto_time = get_data(session_id, n_intervals)
    node_labels = [
        {"label": f"Node {node}", "value": node}
        for node in sorted(
            [node for node in df_full.node.unique() if node != "Unknown"]
        )
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
    selection, nodes, apriori, session_id, n_intervals,
):
    df_full, df_down, auto_time = get_data(session_id, n_intervals)

    df_ant = df_full[df_full.ant == df_full.ant.unique()[0]]
    df_ant = df_ant[df_ant.pol == df_ant.pol.unique()[0]]

    if nodes is not None and isinstance(nodes, str):
        nodes = [nodes]
    elif nodes is None or len(nodes) == 0:
        nodes = df_down.node.unique()

    if apriori is not None and isinstance(apriori, str):
        apriori = [apriori]
    elif apriori is None or len(apriori) == 0:
        apriori = df_down.apriori.unique()

    # use context to tell if selection was made
    ctx = dash.callback_context

    if not ctx.triggered:
        dropdown = False
    else:
        dropdown = "dropdown" in ctx.triggered[0]["prop_id"].split(".")[0]
    if dropdown:
        return plot_df(df_down, nodes, apriori)
    elif (
        selection is not None
        and "xaxis.range[0]" in selection
        and "xaxis.range[1]" in selection
        and len(
            df_ant[
                (df_ant.freqs >= selection["xaxis.range[0]"])
                & (df_ant.freqs <= selection["xaxis.range[1]"])
            ]
        )
        < max_points
    ):
        return plot_df(df_full, nodes, apriori)
    else:
        return plot_df(df_down, nodes, apriori)
