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

from dashboard.models import CommissioningIssue


old_notebook_link = (
    "https://github.com/HERA-Team/H3C_plots/blob/master/data_inspect_{}.ipynb"
)
new_notebook_types = ["all_ants", "known_good", "maybe_good"]
new_notebooks = [
    f"https://github.com/HERA-Team/H4C_Notebooks/blob/master/data_inspect_{notebook_type}/data_inspect_{notebook_type}_{{}}.ipynb"
    for notebook_type in new_notebook_types
]

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
old_notebook_view = old_notebook_link.replace(
    "github.com", "nbviewer.jupyter.org/github"
)
new_notebook_views = [
    nb.replace("github.com", "nbviewer.jupyter.org/github") for nb in new_notebooks
]
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

        if issue.julian_date >= 2459078:
            notebook = ""
            for nb, name in zip(new_notebook_views, new_notebook_types):
                url = nb.format(issue.julian_date)
                notebook += f"[{name}]({url}) "

        else:
            url = old_notebook_view.format(issue.julian_date)
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
                        dbc.Col(
                            dash_table.DataTable(
                                id="table_com",
                                columns=[
                                    {"name": i, "id": i, "presentation": "markdown"}
                                    for i in df
                                ],
                                data=df.to_dict("records"),
                                page_size=20,
                                style_cell={
                                    "textAlign": "center",
                                    "whiteSpace": "normal",
                                },
                                style_header={"fontWeight": "bold", "fontSize": 18,},
                                style_data_conditional=[
                                    {
                                        "if": {"row_index": "odd"},
                                        "backgroundColor": "rgb(248, 248, 248)",
                                    }
                                ],
                                style_table={"height": "90%", "width": "100%",},
                                style_cell_conditional=[
                                    {
                                        "if": {"column_id": "Julian Date"},
                                        "width": "20%",
                                    },
                                    {
                                        "if": {"column_id": "Related Issues"},
                                        "width": "15%",
                                    },
                                    {
                                        "if": {"column_id": "Issue Labels"},
                                        "width": "15%",
                                    },
                                    {
                                        "if": {"column_id": "Nightly Notebook"},
                                        "width": "20%",
                                    },
                                    {
                                        "if": {"column_id": "RFI Notebook"},
                                        "width": "20%",
                                    },
                                    {
                                        "if": {
                                            "column_id": "New Issues Opened On This Day"
                                        },
                                        "width": "10%",
                                    },
                                ],
                            ),
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
                style={"height": "100%", "width": "90%"},
            ),
        ],
        style={"display": "flex", "justify-content": "center"},
    )


app_name = "dash_commissioning_issue"

dash_app = DjangoDash(
    name=app_name,
    serve_locally=False,
    app_name=app_name,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    add_bootstrap_links=True,
)

dash_app.layout = serve_layout


@dash_app.callback(
    [Output("table_com", "data"), Output("table_com", "page_current"),],
    [Input("session-id", "children"), Input("interval-component", "n_intervals"),],
    [State("table_com", "page_current")],
)
def refresh_data(session_id, n_intervals, page_number):
    return get_data(session_id).to_dict("records"), page_number
