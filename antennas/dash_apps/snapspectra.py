"""A dash app to plot snapspectra."""

import re
import numpy as np
import pandas as pd

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objs as go

from django_plotly_dash import DjangoDash

from antennas.models import SnapSpectra, SnapStatus, AntennaStatus


def plot_df(df, hostname):
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

data = []
for unique_hosts in (
    SnapSpectra.objects.order_by().values("hostname", "input_number").distinct()
):
    hostname = unique_hosts["hostname"]
    loc_num = unique_hosts["input_number"]
    match = re.search(r"heraNode(?P<node>\d+)Snap(?P<snap>\d+)", hostname)
    node = int(match.group("node"))
    snap = int(match.group("snap"))

    last_spectra = SnapSpectra.objects.filter(
        hostname=hostname, input_number=loc_num
    ).last()
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
    ant_stat = AntennaStatus.objects.filter(
        snap_hostname=hostname, snap_channel_number=loc_num
    ).last()
    if ant_stat is not None:
        mc_name = f"{ant_stat.antenna.ant_number}{ant_stat.antenna.polarization}"
    freqs = np.linspace(0, 250, spectra.size)
    data.extend(
        [
            {
                "time": last_spectra.time,
                "hostname": hostname,
                "loc_num": loc_num,
                "node": node,
                "snap": snap,
                "mc_name": mc_name,
                "spectra": s,
                "freqs": f,
            }
            for f, s in zip(freqs, spectra)
        ]
    )

df = pd.DataFrame(data)
if not df.empty:
    df.sort_values(
        ["node", "snap", "loc_num", "freqs"], ignore_index=True, inplace=True
    )

dropdown_labels = {}
hostlist = df.hostname.unique()
for hostname in hostlist:
    stat = SnapStatus.objects.filter(hostname=hostname).last()
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

dash_app.layout = html.Div(
    [
        dbc.Row(
            [
                html.Label(
                    [
                        "Snap:",
                        dcc.Dropdown(
                            id="hostname-dropdown",
                            options=[
                                {"label": host, "value": host} for host in hostlist
                            ],
                            multi=False,
                            value=hostlist[0],
                            clearable=False,
                            style={"width": "100%", "display": "inline-block"},
                        ),
                    ],
                    style={"width": "15%"},
                ),
                html.Div(id="snap-stats", style={"padding-left": "1em"}),
            ],
            justify="center",
            align="center",
        ),
        dcc.Graph(
            figure=plot_df(df, hostname=hostlist[0]),
            id="dash_app",
            config={"doubleClick": "reset"},
            responsive=True,
            style={"height": "85%"},
        ),
    ],
    style={"height": "100%", "width": "100%"},
)


@dash_app.callback(
    [Output("dash_app", "figure"), Output("snap-stats", "children"),],
    [Input("hostname-dropdown", "value"),],
)
def redraw_statistic(hostname):
    return plot_df(df, hostname=hostname), dropdown_labels[hostname]
