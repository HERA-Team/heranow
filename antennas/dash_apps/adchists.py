"""A dash application to plot autospectra."""
import re

import copy
import numpy as np
import pandas as pd

from astropy.time import Time

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from ..models import Antenna, AntennaStatus, AprioriStatus


def plot_df(df, nodes=None, apriori=None):
    hovertemplate = "(%{x:.1},\t%{y})<br>%{fullData.text}"
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
            if _df1.node[0] not in nodes or _df1.apriori[0] not in apriori:
                continue
            timestamp = Time(_df1.time[0], format="datetime")
            trace = go.Scatter(
                x=_df1.bins,
                y=_df1.adchist,
                name=antpol,
                mode="lines",
                hovertemplate=hovertemplate,
                text=f"observed at {timestamp.iso}<br>(JD {timestamp.jd:.3f})",
                meta=[_df1.node[0], _df1.apriori[0]],
            )
            fig.add_trace(trace)
    return fig


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

df = pd.DataFrame()

for antenna in Antenna.objects.all():
    stat = AntennaStatus.objects.filter(antenna=antenna).order_by("time").last()
    if stat is not None:
        node = "Unknown"
        match = re.search(r"heraNode(?P<node>\d+)Snap", stat.snap_hostname)
        if match is not None:
            node = int(match.group("node"))

        apriori = "Unknown"
        apriori_stat = (
            AprioriStatus.objects.filter(antenna=stat.antenna).order_by("time").last()
        )
        if apriori_stat is not None:
            apriori = apriori_stat.apriori_status
        if stat.adc_hist is not None:
            data = [
                {
                    "bins": _bin,
                    "adchist": _hist,
                    "ant": stat.antenna.ant_number,
                    "pol": f"{stat.antenna.polarization}",
                    "node": node,
                    "apriori": apriori,
                    "time": stat.time,
                }
                for _bin, _hist in zip(stat.adc_hist[0], stat.adc_hist[1])
            ]
            df1 = pd.DataFrame(data)

            df = df.append(df1)
# Sort according to increasing bins and antpols
if not df.empty:
    df = df.sort_values(["bins", "ant", "pol"])

dash_app.layout = html.Div(
    [
        dbc.Row([], justify="center", align="center"),
        dbc.Row(
            [
                html.Label(
                    [
                        "Node(s):",
                        dcc.Dropdown(
                            id="node-dropdown",
                            options=[
                                {"label": f"Node {node}", "value": node}
                                for node in sorted(
                                    [
                                        node
                                        for node in df.node.unique()
                                        if node != "Unknown"
                                    ]
                                )
                            ]
                            + [{"label": "Unknown Node", "value": "Unknown"}],
                            multi=True,
                            style={"width": "100%"},
                        ),
                    ],
                    style={"width": "40%"},
                ),
                html.Label(
                    [
                        "Apriori Status(es):",
                        dcc.Dropdown(
                            id="apriori-dropdown",
                            options=[
                                {"label": f"{apriori[1]}", "value": apriori[0]}
                                for apriori in AprioriStatus.AprioriStatusList.choices
                            ],
                            multi=True,
                            style={"width": "100%"},
                        ),
                    ],
                    style={"width": "40%"},
                ),
            ],
            justify="center",
            align="center",
        ),
        dcc.Graph(
            figure=plot_df(df),
            id="dash_app",
            config={"doubleClick": "reset"},
            responsive=True,
            style={"height": "90%"},
        ),
    ],
    style={"height": "100%", "width": "100%"},
)


@dash_app.callback(
    Output("dash_app", "figure"),
    [
        Input("dash_app", "relayoutData"),
        Input("node-dropdown", "value"),
        Input("apriori-dropdown", "value"),
    ],
)
def draw_undecimated_data(selection, node_value, apriori_value):
    return plot_df(df, node_value, apriori_value)
