"""Dash App to create Table of hookup notes."""
import re
import uuid
import numpy as np
import pandas as pd

from functools import lru_cache

import dash
import dash_table
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import dash_html_components as html

from django_plotly_dash import DjangoDash

from antennas.models import HookupNotes, Antenna, AntennaStatus, AprioriStatus


@lru_cache
def get_data(session_id):
    data = []
    for ant in Antenna.objects.values("ant_number", "ant_name").distinct():
        stat = AntennaStatus.objects.filter(
            antenna__ant_number=ant["ant_number"]
        ).last()

        node = "Unknown"
        apriori = "Unknown"
        if stat is not None:
            match = re.search(r"heraNode(?P<node>\d+)Snap", stat.snap_hostname)
            if match is not None:
                node = int(match.group("node"))

            apriori_stat = (
                AprioriStatus.objects.filter(antenna=stat.antenna)
                .order_by("time")
                .last()
            )
            if apriori_stat is not None:
                apriori = apriori_stat.apriori_status

        note_text = """"""
        for note in HookupNotes.objects.filter(ant_number=ant["ant_number"]):
            note_text += f"""**{note.part}** ({note.time})  {note.note}  \n"""

        data.append(
            {
                "Antenna": ant["ant_name"],
                "node": node,
                "apriori": apriori,
                "ant_number": ant["ant_number"],
                "Hookup Notes": note_text,
            }
        )
    df = pd.DataFrame(data)
    df.sort_values("ant_number", inplace=True)
    return df


def serve_layout():
    session_id = str(uuid.uuid4())
    df = get_data(session_id)
    return html.Div(
        [
            html.Div(session_id, id="session-id", style={"display": "none"}),
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
                                        + [
                                            {
                                                "label": "Unknown Node",
                                                "value": "Unknown",
                                            }
                                        ],
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
                                                "label": f"{apriori[1]}",
                                                "value": apriori[0],
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
                        style={"height": "10%"},
                    ),
                    dash_table.DataTable(
                        id="table",
                        columns=[
                            {"name": i, "id": i, "presentation": "markdown"}
                            for i in df.loc[:, ["Antenna", "Hookup Notes"]]
                        ],
                        data=df.to_dict("records"),
                        page_size=20,
                        style_cell={
                            "textAlign": "left",
                            "whiteSpace": "normal",
                            "height": "auto",
                        },
                        style_header={"fontWeight": "bold", "fontSize": 18,},
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "rgb(248, 248, 248)",
                            }
                        ],
                        style_table={"height": "90%"},
                    ),
                ],
                style={"height": "100%", "width": "100%"},
            ),
        ],
        style={"display": "flex", "justify-content": "center"},
    )


app_name = "dash_hookup_notes"

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
    Output("node-dropdown", "options"),
    [Input("session-id", "children"), Input("interval-component", "n_intervals")],
)
def update_node_selection(session_id, n_intervals):
    df = get_data(session_id, n_intervals)
    node_labels = [
        {"label": f"Node {node}", "value": node}
        for node in sorted([node for node in df.node.unique() if node != "Unknown"])
    ] + [{"label": "Unknown Node", "value": "Unknown"}]
    return node_labels


@dash_app.callback(
    [
        Output(component_id="table", component_property="data"),
        Output(component_id="table", component_property="page_current"),
    ],
    [
        Input("node-dropdown", "value"),
        Input("apriori-dropdown", "value"),
        Input("session-id", "children"),
    ],
)
def reload_notes(nodes, apriori, session_id):
    df = get_data(session_id)
    if nodes is None or len(nodes) == 0:
        nodes = df.node.unique()

    if apriori is None or len(apriori) == 0:
        apriori = df.apriori.unique()

    df1 = df[(df.node.isin(nodes)) & (df.apriori.isin(apriori))]

    return df1.to_dict("records"), 0
