"""Dash App to create Table of hookup notes."""
import re
import numpy as np
import pandas as pd

import dash
import dash_table
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import dash_html_components as html
import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from antennas.models import HookupNotes, Antenna, AntennaStatus, AprioriStatus


def process_string(input_str, time_string_offset=37):
    # the header is already 37 characters long
    # take this offset into account but only on the first iteration
    if len(input_str) > 80 - time_string_offset:
        space_ind = 79 - time_string_offset

        if " " in input_str[space_ind:]:
            space_ind += input_str[space_ind:].index(" ")

            input_str = (
                input_str[:space_ind]
                + "<br>\t\t\t\t\t\t\t\t"
                + process_string(input_str[space_ind:], time_string_offset=8)
            )
    return input_str


app_name = "dash_hex_notes"

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


data = []
for ant in Antenna.objects.values("ant_number", "ant_name").distinct():
    antenna = Antenna.objects.filter(ant_number=ant["ant_number"]).last()
    stat = AntennaStatus.objects.filter(antenna__ant_number=ant["ant_number"]).last()
    node = "Unknown"
    apriori = "Unknown"
    if stat is not None:
        match = re.search(r"heraNode(?P<node>\d+)Snap", stat.snap_hostname)
        if match is not None:
            node = int(match.group("node"))

        apriori_stat = (
            AprioriStatus.objects.filter(antenna=stat.antenna).order_by("time").last()
        )
        if apriori_stat is not None:
            apriori = apriori_stat.apriori_status

    note_text = f"""{ant['ant_name']}<br>"""
    for note in HookupNotes.objects.filter(ant_number=ant["ant_number"]):
        notes = process_string(note.note)
        note_text += f"""    {note.part} ({note.time})  {notes}<br>"""

    # take on some text if there was nothing
    if note_text == f"""{ant['ant_name']}<br>""":
        note_text += "No Notes Information"

    data.append(
        {
            "Antenna": ant["ant_name"],
            "node": node,
            "apriori": apriori,
            "ant_number": ant["ant_number"],
            "text": note_text,
            "antpos_x": antenna.antpos_enu[0],
            "antpos_y": antenna.antpos_enu[1],
            "constructed": antenna.constructed,
            "color": "green"
            if stat is not None
            else "red"
            if antenna.constructed
            else "black",
            "opacity": 1 if stat is not None else 0.2,
        }
    )
df = pd.DataFrame(data)
df.sort_values("ant_number", inplace=True)

dash_app.layout = html.Div(
    [
        html.Div(
            [
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
                    id="graph",
                    config={"doubleClick": "reset"},
                    responsive=True,
                    style={"height": "90%"},
                ),
            ],
            style={"height": "100%", "width": "100%"},
        ),
    ],
    style={"height": "100%", "width": "100%"},
)


@dash_app.callback(
    Output(component_id="graph", component_property="figure"),
    [Input("node-dropdown", "value"), Input("apriori-dropdown", "value"),],
)
def reload_notes(nodes, apriori):

    if nodes is None or len(nodes) == 0:
        nodes = df.node.unique()

    if apriori is None or len(apriori) == 0:
        apriori = df.apriori.unique()

    hovertemplate = "%{text}<extra></extra>"

    layout = {
        "xaxis": {"title": "East-West Position [m]", "constrain": "domain",},
        "yaxis": {
            "title": "North-South Position [m]",
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        "title": {"text": "Per Antpol Stats vs Hex position", "font": {"size": 24},},
        "hoverlabel": {"align": "left"},
        "margin": {"t": 40},
        "autosize": True,
        "showlegend": False,
        "hovermode": "closest",
    }
    fig = go.Figure()
    fig["layout"] = layout

    df1 = df[(df.node.isin(nodes)) & (df.apriori.isin(apriori))]
    # trace = go.Scatter(
    #     x=df1[~df1.constructed].antpos_x,
    #     y=df1[~df1.constructed].antpos_y,
    #     mode="markers",
    #     marker={
    #         "color": df[~df.constructed].color,
    #         "size": 14,
    #         "symbol": "hexagon",
    #         "opacity": df[~df.constructed].opacity,
    #     },
    #     text=df1[~df1.constructed].text,
    #     hovertemplate=hovertemplate,
    # )
    # fig.add_trace(trace)

    trace = go.Scatter(
        x=df1.antpos_x,
        y=df1.antpos_y,
        mode="markers",
        marker={
            "color": df1.color,
            "size": 14,
            "symbol": "hexagon",
            "opacity": df1.opacity,
        },
        text=df1.text,
        hovertemplate=hovertemplate,
    )
    fig.add_trace(trace)

    return fig
