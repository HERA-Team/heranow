"""Dash App to create Table of hookup notes."""
import re
import uuid
import numpy as np
import pandas as pd

from functools import lru_cache
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, timezone

import dash
import dash_table
import dash_daq as daq
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import dash_html_components as html

from django_plotly_dash import DjangoDash

from dashboard.models import HookupNotes, Antenna, AntennaStatus, AprioriStatus


def get_marks_from_start_end(start, end):
    """Generate the time selection points for webpage slider.

    Parameters
    ----------
    start : Datetime Object
        Earliest date to draw mark on slider
    end : Datetime object
        Latest date to draw mark on slider

    Returns
    -------
    dict with one item per month keyed by unix timestamp

    """
    result = []
    current = start
    while current <= end:
        result.append(current)
        current += relativedelta(months=2)

    return {int(m.timestamp()): str(m.strftime("%Y-%m")) for m in result}


@lru_cache(maxsize=32)
def get_data(session_id):
    """Query Database and prepare data as DataFrame.

    Parameters
    ----------
    session_id : str
        unique session id hex used for caching.

    Returns
    -------
    pandas DataFrame of hookup notes for each antenna.

    """
    data = []

    for ant in Antenna.objects.values("ant_number", "ant_name").distinct():
        try:
            stat = AntennaStatus.objects.filter(
                antenna__polarization="e", antenna__ant_number=ant["ant_number"]
            ).latest("time")
        except AntennaStatus.DoesNotExist:
            stat = None

        node = "Unknown"
        apriori = "Unknown"
        if stat is not None:
            if ant["ant_number"] == 11:
                print(stat.snap_hostname)
            match = re.search(r"heraNode(?P<node>\d+)Snap", stat.snap_hostname)
            if match is not None:
                node = int(match.group("node"))

            apriori_stat = (
                AprioriStatus.objects.filter(antenna=stat.antenna)
                .order_by("time")
                .last()
            )
            if apriori_stat is not None:
                apriori = apriori_stat.get_apriori_status_display()

        for note in HookupNotes.objects.filter(ant_number=ant["ant_number"]):

            data.append(
                {
                    "Antenna": ant["ant_name"],
                    "node": node,
                    "part": note.part,
                    "time": note.time,
                    "apriori": apriori,
                    "ant_number": ant["ant_number"],
                    "is_apriori": note.reference == "apa-infoupd",
                    "Hookup Notes": f"""**{note.part}** ({note.time})  {note.note} """,
                }
            )
    df = pd.DataFrame(data)
    df.sort_values(
        ["ant_number", "part", "time"],
        ascending=[True, True, False],
        ignore_index=True,
        inplace=True,
    )

    return df


def serve_layout():
    """Render layout of webpage.

    Returns
    -------
    Div of application used in web rendering.

    """
    session_id = str(uuid.uuid4())
    df = get_data(session_id)
    return html.Div(
        [
            html.Div(session_id, id="session-id", style={"display": "none"}),
            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                daq.BooleanSwitch(
                                    id="apa-only",
                                    on=False,
                                    label="Apriori Notes Only",
                                    labelPosition="top",
                                    style={"text-align": "center"},
                                ),
                                width=1,
                            ),
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
                    dbc.Row(
                        dbc.Col(
                            dcc.RangeSlider(
                                id="datetime-slider",
                                updatemode="mouseup",
                                min=df.time.min().timestamp(),
                                max=datetime.now(tz=timezone.utc).timestamp(),
                                step=10000,
                                value=[
                                    df.time.min().timestamp(),
                                    datetime.now(tz=timezone.utc).timestamp(),
                                ],
                                marks=get_marks_from_start_end(
                                    df.time.min(), datetime.now(tz=timezone.utc)
                                ),
                            ),
                        ),
                    ),
                    dash_table.DataTable(
                        id="table",
                        columns=[
                            {"name": i.title(), "id": i, "presentation": "markdown"}
                            for i in df.loc[
                                :, ["Antenna", "node", "apriori", "Hookup Notes"]
                            ]
                        ],
                        data=[
                            {
                                "Antenna": "Loading",
                                "node": "Data",
                                "apriori": "Please",
                                "Hookup Notes": "Wait",
                            }
                        ],
                        page_size=20,
                        style_cell={
                            "textAlign": "left",
                            "whiteSpace": "normal",
                            "height": "auto",
                        },
                        style_header={
                            "fontWeight": "bold",
                            "fontSize": 18,
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "rgb(248, 248, 248)",
                            }
                        ],
                    ),
                ],
                style={"height": "100%", "width": "100%"},
            ),
        ],
        style={"height": "100%", "justify-content": "center"},
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
    [Input("session-id", "children")],
)
def update_node_selection(session_id):
    """Update node selection button."""
    df = get_data(session_id)
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
        Input("datetime-slider", "value"),
        Input("apa-only", "on"),
    ],
)
def reload_notes(nodes, apriori, session_id, time_range, apa_only):
    """Reload notes for display based on user input."""
    df = get_data(session_id)
    if nodes is None or len(nodes) == 0:
        nodes = df.node.unique()

    if apriori is None or len(apriori) == 0:
        apriori = df.apriori.unique()

    df1 = df[(df.node.isin(nodes)) & (df.apriori.isin(apriori))]
    if apa_only:
        df1 = df1[df1.is_apriori]
    df1 = (
        df1[
            (datetime.fromtimestamp(time_range[0], tz=timezone.utc) <= df1.time)
            & (df1.time <= datetime.fromtimestamp(time_range[1], tz=timezone.utc))
        ]
        .groupby("Antenna")
        .aggregate(
            {
                "ant_number": "first",
                "node": "first",
                "apriori": "first",
                "Hookup Notes": " \n".join,
            }
        )
    )
    df2 = df1["Hookup Notes"].to_frame()
    df2["apriori"] = df1["apriori"]
    df2["ant_number"] = pd.to_numeric(df1["ant_number"], errors="ignore")
    df2["node"] = pd.to_numeric(df1["node"], errors="ignore")
    df2.reset_index(inplace=True)
    df2.sort_values("ant_number", inplace=True)

    return df2.to_dict("records"), 0
