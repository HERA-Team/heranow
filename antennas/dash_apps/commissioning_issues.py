import re
import os
import copy
import uuid
import github3
import datetime
import requests
import numpy as np
import pandas as pd
from astropy.time import Time

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

from django_plotly_dash import DjangoDash

from antennas.models import CommissioningIssue


notebook_link = (
    "https://github.com/HERA-Team/H3C_plots/blob/master/data_inspect_{}.ipynb"
)
issue_link = "https://github.com/HERA-Team/HERA_Commissioning/issues/{}"
new_issue_link = (
    "https://github.com/HERA-Team/HERA_Commissioning/issues"
    "/new?assignees=&labels=Daily&template=daily-log.md"
    "&title=Observing+report+{}"
)
rfi_link = (
    "https://github.com/alphatangojuliett/HERA_daily_RFI"
    "/blob/herapost-master/daily_RFI_report_{}.ipynb"
)

label_link = 'https://github.com/HERA-Team/HERA_Commissioning/issues?q=is%3Aissue+is%3Aopen+label%3A"{}"'
notebook_view = notebook_link.replace("github.com", "nbviewer.jupyter.org/github")
rfi_view = rfi_link.replace("github.com", "nbviewer.jupyter.org/github")


def get_data(session_id):
    data = []
    for issue in CommissioningIssue.objects.all():
        related = []
        labels = []

        if issue.number is not None:
            iss_text = f"[{issue.julian_date}]({issue_link.format(issue.number)})"
            if issue.labels is not None:
                labels = [
                    f"[{lab}]({label_link.format(lab.replace(' ', '+'))})"
                    for lab in issue.labels
                ]

            if issue.related_issues is not None:
                related = [
                    f"[{iss}]({issue_link.format(iss)})" for iss in issue.related_issues
                ]
        else:
            iss_text = f"[{issue.julian_date} No Entry]({new_issue_link.format(issue.julian_date)})"
        related = " ".join(related)
        labels = " ".join(labels)

        url = notebook_view.format(issue.julian_date)
        notebook = f"[Check Availability]({url})"

        obs_date = Time(issue.julian_date, format="jd")
        request_date = obs_date.isot.split("T")[0].replace("-", "")
        url = rfi_view.format(request_date)
        rfi = f"[Check Availability]({url})"

        data.append(
            {
                "Julian Date": iss_text,
                "Related Issues": related,
                "Issue Labels": labels,
                "Nightly Notebook": notebook,
                "RFI Notebook": rfi,
                "New Issues Opened On This Day": issue.new_issues,
            }
        )

    df = pd.DataFrame(data)
    if not df.empty:
        df.sort_values(["Julian Date"], inplace=True, ascending=False)
        df.reset_index(drop=True, inplace=True)
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
                        [], justify="center", align="center", style={"height": "10%"},
                    ),
                    dbc.Row(
                        dash_table.DataTable(
                            id="table",
                            columns=[
                                {"name": i, "id": i, "presentation": "markdown"}
                                for i in df
                            ],
                            data=df.to_dict("records"),
                            page_size=20,
                            style_cell={
                                "textAlign": "center",
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
                            style_table={
                                "height": "90%",
                                "width": "80%",
                                "padding-left": "5em",
                                "padding-right": "5em",
                                "table-layout": "fixed",
                            },
                            style_cell_conditional=[
                                {
                                    "if": {
                                        "column_id": "New Issues Opened On This Day"
                                    },
                                    "min-width": "100px",
                                },
                                {
                                    "if": {
                                        "column_id": "New Issues Opened On This Day"
                                    },
                                    "width": "75px",
                                    "min-width": "25px",
                                },
                                {
                                    "if": {"column_id": "Related Issues"},
                                    "width": "100px",
                                },
                                {"if": {"column_id": "Issue Labels"}, "width": "100px"},
                            ],
                        ),
                        justify="center",
                        align="center",
                    ),
                    dcc.Interval(
                        id="interval-component",
                        interval=5 * 60 * 1000,
                        n_intervals=0,
                        disabled=False,
                    ),
                ],
                style={"height": "100%", "width": "100%"},
            ),
        ],
        style={"display": "flex", "justify-content": "center"},
    )


app_name = "dash_commissioning_issue"

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
    [Output("table", "data"), Output("table", "page_current"),],
    [Input("session-id", "children"), Input("interval-component", "n_intervals"),],
    [State("table", "page_current")],
)
def refresh_data(session_id, n_intervals, page_number):
    return get_data(session_id).to_dict("records"), page_number
