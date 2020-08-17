"""A dash application to plot autospectra."""
import re

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


def get_data():
    df_full = pd.DataFrame()
    df_down = pd.DataFrame()

    last_spectra = AutoSpectra.objects.last()
    if last_spectra is not None:
        auto_time = Time(last_spectra.time, format="datetime")
        all_spectra = AutoSpectra.objects.filter(time=last_spectra.time).order_by(
            "antenna"
        )

        for stat in all_spectra:
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
                apriori = apriori_stat.apriori_status

            _freqs = np.asarray(stat.frequencies) / 1e6
            _spectra = (10 * np.log10(np.ma.masked_invalid(stat.spectra))).filled(-100)
            # _freqs = freqs / 1e6
            # _spectra = spectra
            data = [
                {
                    "freqs": f,
                    "spectra": d,
                    "ant": stat.antenna.ant_number,
                    "pol": f"{stat.antenna.polarization}",
                    "node": node,
                    "apriori": apriori,
                }
                for f, d in zip(_freqs, _spectra)
            ]
            df1 = pd.DataFrame(data)

            df_full = df_full.append(df1)
            downsampled = lttb.downsample(np.stack([_freqs, _spectra,], axis=1), 350,)
            data1 = [
                {
                    "freqs": f,
                    "spectra": d,
                    "ant": stat.antenna.ant_number,
                    "pol": f"{stat.antenna.polarization}",
                    "node": node,
                    "apriori": apriori,
                }
                for f, d in zip(downsampled[:, 0], downsampled[:, 1])
            ]
            df1 = pd.DataFrame(data1)
            df_down = df_down.append(df1)
    else:
        return None, None, Time(0, format="jd")

    if not df_full.empty:
        # Sort according to increasing frequencies and antpols
        df_full.sort_values(["freqs", "ant", "pol"], inplace=True)
        df_down.sort_values(["freqs", "ant", "pol"], inplace=True)
        df_full.reset_index(drop=True, inplace=True)
        df_down.reset_index(drop=True, inplace=True)

    return df_full, df_down, auto_time


def plot_df(df, nodes=None, apriori=None):

    hovertemplate = (
        "%{x:.1f}\tMHz<br>%{y:.3f}\t[dB]"
        "<extra>%{fullData.name}<br>Node: %{meta[0]}<br>Status: %{meta[1]}</extra>"
    )
    if nodes is not None and isinstance(nodes, str):
        nodes = [nodes]
    elif nodes is None or len(nodes) == 0:
        nodes = df.node.unique()

    if apriori is not None and isinstance(apriori, str):
        apriori = [apriori]
    elif apriori is None or len(apriori) == 0:
        apriori = df.apriori.unique()

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
    fig["layout"]["uirevision"] = f"{nodes} {apriori}"
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


max_points = 4000

timestamp = Time(0, format="jd")
init_time_ago = (Time.now() - timestamp).to("min")
init_time_color = "red"

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


dash_app.layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    daq.BooleanSwitch(
                        id="reload-box",
                        on=False,
                        label="Reload Data",
                        labelPosition="top",
                    ),
                ),
                dbc.Col(
                    html.Div(
                        id="auto-time",
                        children=[
                            html.Span(
                                "Autocorrelations from ", style={"font-weight": "bold"}
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
                    style={"width": 3},
                ),
            ],
            justify="center",
            align="center",
        ),
        dbc.Row(
            [
                html.Label([""], style={"width": "10%"}),
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
        # dcc.Loading(
        dcc.Graph(
            id="dash_app", config={"doubleClick": "reset"}, style={"height": "85%"},
        ),
        # ),
        # Hidden div inside the app that stores the intermediate value
        html.Div(
            id="intermediate-value",
            style={"display": "none"},
            children=[pd.DataFrame().to_json(), pd.DataFrame().to_json(), timestamp.jd],
        ),
        # A timer to re-load data every minute
        # interval value is milliseconds
        dcc.Interval(id="interval-component", interval=60 * 1000, n_intervals=0),
    ],
    style={"height": "100%", "width": "100%"},
)


@dash_app.callback(
    Output("intermediate-value", "children"),
    [Input("interval-component", "n_intervals")],
    [State("reload-box", "on")],
)
def reload_data(n_intervals, reload_box):
    print("Checking: ", end="")
    if reload_box or n_intervals == 0:
        df_full, df_down, auto_time = get_data()
        print("Loading")
        hidden_div = [df_full.to_json(), df_down.to_json(), auto_time.jd]
        return hidden_div
    else:
        print("Skip")
        raise PreventUpdate()


@lru_cache
def read_json_data(hidden_div):
    print("Reading Data")
    df_full = pd.read_json(hidden_div[0])
    df_down = pd.read_json(hidden_div[1])
    auto_time = Time(hidden_div[2], format="jd")
    return df_full, df_down, auto_time


@dash_app.callback(
    Output("auto-time", "children"), [Input("intermediate-value", "children")],
)
def update_time_data(hidden_div):
    print("Updating time info")
    df_full, df_down, auto_time = read_json_data(tuple(hidden_div))

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
    Output("node-dropdown", "options"), [Input("intermediate-value", "children")],
)
def update_node_selection(hidden_div):
    print("making labels")
    df_full, df_down, auto_time = read_json_data(tuple(hidden_div))
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
        Input("intermediate-value", "children"),
    ],
)
def draw_undecimated_data(selection, node_value, apriori_value, hidden_div):
    print("plotting Time!")
    df_full, df_down, auto_time = read_json_data(tuple(hidden_div))

    df_ant = df_full[df_full.ant == df_full.ant.unique()[0]]
    df_ant = df_ant[df_ant.pol == df_ant.pol.unique()[0]]

    if (
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
        return plot_df(df_full, node_value, apriori_value)
    else:
        return plot_df(df_down, node_value, apriori_value)
